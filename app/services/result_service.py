from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.mappers.result_mapper import ResultMapper
from app.models.result_approval import ResultApproval
from app.models.result_batch import ResultBatch
from app.models.result_record import ResultRecord
from app.models.result_summary import ResultSummary
from app.models.user import User
from app.repositories.academic_session_repository import academic_session_repo
from app.repositories.result_repository import result_repository
from app.repositories.teacher_assignment_repository import (
    teacher_assignment_repository,
)
from app.repositories.term_repository import term_repo
from app.schemas.result_responses import (
    ClassResultResponse,
    ResultBatchStatusResponse,
    ResultSubmissionResponse,
    StudentResultApiResponse,
)
from app.schemas.result_schema import ResultStatusResponse


class ResultService:
    def __init__(self):
        self.repo = result_repository
        self.assignment_repo = teacher_assignment_repository
        self.session_repo = academic_session_repo
        self.term_repo = term_repo

    def calculate_grade(
        self,
        score: int,
    ) -> tuple[str, str]:
        if score >= 70:
            return "A", "Excellent"

        if score >= 60:
            return "B", "Very Good"

        if score >= 50:
            return "C", "Good"

        if score >= 45:
            return "D", "Fair"

        if score >= 40:
            return "E", "Pass"

        return "F", "Fail"

    async def _save_batch(
        self,
        db,
        payload,
        teacher,
        status: str,
    ):
        active_session = await self.session_repo.get_active(
            db,
            teacher.school_id,
        )

        active_term = await self.term_repo.get_active(
            db,
            teacher.school_id,
        )

        batch = await self.repo.get_current_batch(
            db=db,
            school_id=teacher.school_id,
            class_id=payload.class_id,
            session_id=active_session.id,
            term_id=active_term.id,
        )

        created = batch is None

        if created:
            batch = ResultBatch(
                school_id=teacher.school_id,
                class_id=payload.class_id,
                session_id=active_session.id,
                term_id=active_term.id,
                created_by=teacher.id,
                status=status,
            )

            await self.repo.create_batch(
                db,
                batch,
            )

        else:
            if batch.status not in (
                "DRAFT",
                "SUBMITTED",
                "REJECTED",
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Results can no longer be edited.",
                )

            batch.status = status

            await self.repo.save_batch(
                db,
                batch,
            )

        for student in payload.students:
            for score in student.scores:
                total = score.ca_score + score.exam_score

                grade, remark = self.calculate_grade(
                    total,
                )

                await self.repo.upsert_record(
                    db=db,
                    batch_id=batch.id,
                    school_id=teacher.school_id,
                    student_id=student.student_id,
                    subject_id=score.subject_id,
                    ca_score=score.ca_score,
                    exam_score=score.exam_score,
                    total_score=total,
                    grade=grade,
                    remark=remark,
                    teacher_comment=score.teacher_comment,
                )

        await self._recalculate_batch(
            db=db,
            batch_id=batch.id,
            school_id=teacher.school_id,
        )

        action = (
            "CREATED"
            if created
            else ("SUBMITTED" if status == "SUBMITTED" else "DRAFT_UPDATED")
        )

        await self.repo.create_approval_log(
            db,
            ResultApproval(
                school_id=teacher.school_id,
                batch_id=batch.id,
                action_by=teacher.id,
                action=action,
                action_at=datetime.now(UTC),
            ),
        )

        return batch, created

    async def _recalculate_batch(
        self,
        db,
        batch_id,
        school_id,
    ):
        batch = await self.repo.get_batch_with_records(
            db=db,
            batch_id=batch_id,
            school_id=school_id,
        )

        if not batch:
            return

        totals = defaultdict(int)
        subject_count = defaultdict(int)
        passed = defaultdict(int)
        failed = defaultdict(int)

        for record in batch.records:
            total = record.ca_score + record.exam_score

            grade, remark = self.calculate_grade(total)

            record.total_score = total
            record.grade = grade
            record.remark = remark

            totals[record.student_id] += total
            subject_count[record.student_id] += 1

            if grade == "F":
                failed[record.student_id] += 1
            else:
                passed[record.student_id] += 1

        positions = self.generate_positions(totals)

        summaries = {summary.student_id: summary for summary in batch.summaries}

        for student_id in totals:
            average = round(
                totals[student_id] / subject_count[student_id],
                2,
            )

            if student_id in summaries:
                summary = summaries[student_id]

                summary.total_score = totals[student_id]
                summary.average_score = average
                summary.subjects_offered = subject_count[student_id]
                summary.passed_subjects = passed[student_id]
                summary.failed_subjects = failed[student_id]
                summary.position = positions[student_id]

                await self.repo.save_summary(
                    db,
                    summary,
                )

            else:
                await self.repo.save_summary(
                    db,
                    ResultSummary(
                        school_id=batch.school_id,
                        batch_id=batch.id,
                        student_id=student_id,
                        total_score=totals[student_id],
                        average_score=average,
                        subjects_offered=subject_count[student_id],
                        passed_subjects=passed[student_id],
                        failed_subjects=failed[student_id],
                        position=positions[student_id],
                    ),
                )

    def generate_positions(
        self,
        student_totals: dict,
    ):
        sorted_students = sorted(
            student_totals.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        positions = {}

        current_position = 0
        previous_score = None

        for index, (student_id, score) in enumerate(
            sorted_students,
            start=1,
        ):
            if score != previous_score:
                current_position = index

            positions[student_id] = current_position

            previous_score = score

        return positions

    async def submit_results(
        self,
        db,
        payload,
        teacher,
    ):
        can_manage = await self.assignment_repo.teacher_can_manage_class(
            db,
            teacher.id,
            payload.class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this class.",
            )

        committed = False

        try:
            batch, created = await self._save_batch(
                db=db,
                payload=payload,
                teacher=teacher,
                status="SUBMITTED",
            )

            await self.repo.commit(db)

            committed = True

            return {
                "batch_id": batch.id,
                "created": created,
                "status": batch.status,
                "total_students": len(payload.students),
                "total_records": sum(
                    len(student.scores) for student in payload.students
                ),
                "message": (
                    "Results submitted successfully."
                    if created
                    else "Results updated successfully."
                ),
            }

        finally:
            if not committed:
                await self.repo.rollback(db)

    async def get_editable_batch(
        self,
        db,
        teacher: User,
        class_id,
    ):
        can_manage = await self.assignment_repo.teacher_has_class_access(
            db,
            teacher.id,
            class_id,
        )
        print(can_manage)

        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this class.",
            )

        session = await self.session_repo.get_active(
            db,
            teacher.school_id,
        )

        term = await self.term_repo.get_active(
            db,
            teacher.school_id,
        )

        batch = await self.repo.get_teacher_editable_batch(
            db=db,
            school_id=teacher.school_id,
            class_id=class_id,
            session_id=session.id,
            term_id=term.id,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="No result batch found.",
            )

        if batch.status not in ("DRAFT", "REJECTED", "SUBMITTED"):
            raise HTTPException(
                status_code=400,
                detail="This batch cannot be edited.",
            )

        return ResultMapper.class_result(batch)

    async def resubmit_batch(
        self,
        db,
        batch_id,
        teacher: User,
    ):
        batch = await self.repo.get_batch(
            db,
            batch_id,
            teacher.school_id,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="Batch not found.",
            )

        if batch.status != "REJECTED":
            raise HTTPException(
                status_code=400,
                detail="Only rejected batches can be resubmitted.",
            )

        can_manage = await self.assignment_repo.teacher_has_class_access(
            db,
            teacher.id,
            batch.class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail="You cannot manage this class.",
            )

        committed = False

        try:
            batch.status = "SUBMITTED"
            batch.requires_review = False

            await self.repo.save_batch(
                db,
                batch,
            )

            await self.repo.create_approval_log(
                db,
                ResultApproval(
                    school_id=teacher.school_id,
                    batch_id=batch.id,
                    action_by=teacher.id,
                    action="RESUBMITTED",
                    action_at=datetime.now(UTC),
                ),
            )

            await self.repo.commit(db)

            committed = True

            return {
                "message": "Results resubmitted successfully.",
                "status": batch.status,
            }

        finally:
            if not committed:
                await self.repo.rollback(db)

    async def get_result_status(
        self,
        db,
        teacher: User,
        class_id,
    ):
        can_manage = await self.assignment_repo.teacher_can_manage_class(
            db,
            teacher.id,
            class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this class.",
            )
        active_session = await self.session_repo.get_active(db, teacher.school_id)
        active_term = await self.term_repo.get_active(db, teacher.school_id)

        batch = await self.repo.get_class_result_batch(
            db=db,
            school_id=teacher.school_id,
            class_id=class_id,
            session_id=active_session.id,
            term_id=active_term.id,
        )

        if not batch:
            return ResultStatusResponse(
                exists=False,
            )

        return ResultStatusResponse(
            exists=True,
            editable=batch.status in ["DRAFT", "REJECTED"],
            status=batch.status,
            batch_id=batch.id,
        )

    async def save_draft(
        self,
        db,
        payload,
        teacher,
    ):
        can_manage = await self.assignment_repo.teacher_can_manage_class(
            db,
            teacher.id,
            payload.class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this class.",
            )

        committed = False

        try:
            batch, created = await self._save_batch(
                db=db,
                payload=payload,
                teacher=teacher,
                status="DRAFT",
            )

            await self.repo.commit(db)

            committed = True

            return {
                "batch_id": batch.id,
                "created": created,
                "status": batch.status,
                "message": (
                    "Draft saved successfully."
                    if created
                    else "Draft updated successfully."
                ),
            }

        finally:
            if not committed:
                await self.repo.rollback(db)

    async def get_current_batch(
        self,
        db,
        class_id,
        school_id,
    ):
        active_session = await self.session_repo.get_active(
            db,
            school_id,
        )

        active_term = await self.term_repo.get_active(
            db,
            school_id,
        )

        batch = await self.repo.get_current_batch(
            db=db,
            school_id=school_id,
            class_id=class_id,
            session_id=active_session.id,
            term_id=active_term.id,
        )

        if batch is None:
            return None

        return ResultMapper.class_result(batch)

    async def get_class_batches(
        self,
        db,
        class_id,
        school_id,
    ):
        return await self.repo.get_class_batches(
            db=db,
            school_id=school_id,
            class_id=class_id,
        )

    async def get_batch(
        self,
        db,
        batch_id,
    ):
        batch = await self.repo.get_batch_details(
            db,
            batch_id,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="Batch not found.",
            )

        return ResultMapper.class_result(
            batch,
        )

    async def approve_result(
        self,
        db,
        batch_id,
        admin,
    ):
        batch = await self.repo.get_batch(
            db,
            batch_id,
            admin.school_id,
        )

        if not batch:
            raise HTTPException(
                status_code=404,
                detail="Result batch not found.",
            )

        committed = False

        try:
            batch.status = "APPROVED"

            await self.repo.save_batch(
                db,
                batch,
            )

            await self.repo.create_approval_log(
                db,
                ResultApproval(
                    school_id=admin.school_id,
                    batch_id=batch.id,
                    action_by=admin.id,
                    action="APPROVED",
                    action_at=datetime.now(UTC),
                ),
            )

            await self.repo.commit(
                db,
            )

            committed = True

            return ResultBatchStatusResponse(
                batch_id=batch.id,
                status=batch.status,
                message="Result approved successfully.",
            )

        finally:
            if not committed:
                await self.repo.rollback(
                    db,
                )

    async def reject_result(
        self,
        db,
        batch_id,
        note,
        admin,
    ):
        batch = await self.repo.get_batch(
            db,
            batch_id,
            admin.school_id,
        )

        if not batch:
            raise HTTPException(
                status_code=404,
                detail="Result batch not found.",
            )

        committed = False

        try:
            batch.status = "REJECTED"
            batch.requires_review = True

            await self.repo.save_batch(
                db,
                batch,
            )

            await self.repo.create_approval_log(
                db,
                ResultApproval(
                    school_id=admin.school_id,
                    batch_id=batch.id,
                    action_by=admin.id,
                    action="REJECTED",
                    note=note,
                    action_at=datetime.now(UTC),
                ),
            )

            await self.repo.commit(
                db,
            )

            committed = True

            return ResultBatchStatusResponse(
                batch_id=batch.id,
                status=batch.status,
                message="Result rejected successfully.",
            )

        finally:
            if not committed:
                await self.repo.rollback(
                    db,
                )

    async def publish_result(
        self,
        db,
        batch_id,
        admin,
    ):
        batch = await self.repo.get_batch(
            db,
            batch_id,
            admin.school_id,
        )

        if not batch:
            raise HTTPException(
                status_code=404,
                detail="Result batch not found.",
            )

        if batch.status != "APPROVED":
            raise HTTPException(
                status_code=400,
                detail="Only approved results can be published.",
            )

        committed = False

        try:
            batch.status = "PUBLISHED"
            batch.published_at = datetime.now(UTC)

            await self.repo.save_batch(
                db,
                batch,
            )

            await self.repo.create_approval_log(
                db,
                ResultApproval(
                    school_id=admin.school_id,
                    batch_id=batch.id,
                    action_by=admin.id,
                    action="PUBLISHED",
                    action_at=datetime.now(UTC),
                ),
            )

            await self.repo.commit(
                db,
            )

            committed = True

            return ResultBatchStatusResponse(
                batch_id=batch.id,
                status=batch.status,
                message="Result published successfully.",
            )

        finally:
            if not committed:
                await self.repo.rollback(
                    db,
                )

    async def update_result_record(
        self,
        db,
        record_id,
        payload,
        user: User,
    ):
        committed = False

        try:
            record = await self.repo.get_record(
                db,
                record_id,
            )

            if not record:
                raise HTTPException(
                    status_code=404,
                    detail="Result record not found.",
                )

            batch = await self.repo.get_batch(
                db=db,
                batch_id=record.batch_id,
                school_id=record.school_id,
            )

            if not batch:
                raise HTTPException(
                    status_code=404,
                    detail="Result batch not found.",
                )

            # Teachers can only edit editable batches
            if user.role == "TEACHER":
                can_manage = await self.assignment_repo.teacher_can_manage_class(
                    db,
                    user.id,
                    batch.class_id,
                )

                if not can_manage:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not assigned to this class.",
                    )

                if batch.status not in (
                    "DRAFT",
                    "SUBMITTED",
                    "REJECTED",
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Results can no longer be edited.",
                    )

            total = payload.ca_score + payload.exam_score

            grade, remark = self.calculate_grade(
                total,
            )

            record.ca_score = payload.ca_score
            record.exam_score = payload.exam_score
            record.total_score = total
            record.grade = grade
            record.remark = remark
            record.teacher_comment = payload.teacher_comment

            await self.repo.update_record(
                db,
                record,
            )

            await self._recalculate_batch(
                db=db,
                batch_id=record.batch_id,
                school_id=record.school_id,
            )

            await self.repo.commit(db)
            committed = True

            return {
                "message": "Result updated successfully.",
            }

        finally:
            if not committed:
                await self.repo.rollback(db)

    async def update_teacher_comment(
        self,
        db,
        record_id,
        comment,
    ):
        record = await self.repo.get_record(
            db,
            record_id,
        )

        if not record:
            raise HTTPException(
                status_code=404,
                detail="Result record not found.",
            )

        committed = False

        try:
            record.teacher_comment = comment

            await self.repo.update_record(
                db,
                record,
            )

            await self.repo.commit(
                db,
            )

            committed = True

            return {
                "message": "Teacher comment updated successfully.",
            }

        finally:
            if not committed:
                await self.repo.rollback(
                    db,
                )

    async def get_class_results(
        self,
        db,
        school_id,
        class_id,
        session_id=None,
        term_id=None,
    ):
        if session_id is None:
            active_session = await self.session_repo.get_active(
                db,
                school_id,
            )

            session_id = active_session.id

        if term_id is None:
            active_term = await self.term_repo.get_active(
                db,
                school_id,
            )

            term_id = active_term.id

        batch = await self.repo.get_class_result_batch(
            db=db,
            school_id=school_id,
            class_id=class_id,
            session_id=session_id,
            term_id=term_id,
        )

        # No batch yet -> return empty response
        if batch is None:
            return ClassResultResponse(
                batch_id=None,
                class_id=class_id,
                session_id=session_id,
                term_id=term_id,
                status="NOT_UPLOADED",
                editable=True,
                subjects=[],
                students=[],
            )

        return ResultMapper.class_result(batch)

    async def get_student_result(
        self,
        db,
        student,
        session_id,
        term_id,
    ):
        result = await self.repo.get_student_published_result(
            db,
            student.school_id,
            student.id,
            session_id,
            term_id,
        )

        if not result:
            return StudentResultApiResponse(
                published=False,
                message="Your result has not been published yet.",
                data=None,
            )

        return StudentResultApiResponse(
            published=True,
            message="Result available.",
            data=ResultMapper.student_result(result),
        )

    async def get_student_result_for_pdf(
        self,
        db,
        student,
        session_id,
        term_id,
    ):
        # Load student profile (admission number)
        user = (
            await db.execute(
                select(User)
                .options(
                    selectinload(User.student_profile),
                )
                .where(
                    User.id == student.id,
                )
            )
        ).scalar_one()

        result = await self.repo.get_student_published_result(
            db=db,
            school_id=student.school_id,
            student_id=student.id,
            session_id=session_id,
            term_id=term_id,
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Result has not been published.",
            )

        response = ResultMapper.student_result(result)

        batch = result["batch"]
        school = batch.school

        return {
            # =====================================
            # SCHOOL INFORMATION
            # =====================================
            "school": {
                "id": school.id if school else None,
                "name": school.name if school else "",
                "logo": getattr(school, "logo", None),
                "address": getattr(school, "address", ""),
                "phone": getattr(school, "phone_number", ""),
                "email": getattr(school, "email", ""),
                "website": getattr(school, "website", ""),
            },
            # =====================================
            # STUDENT INFORMATION
            # =====================================
            "student": {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}",
                "first_name": student.first_name,
                "last_name": student.last_name,
                "admission_number": getattr(
                    user.student_profile,
                    "admission_number",
                    None,
                ),
                "class_name": (batch.school_class.name if batch.school_class else ""),
            },
            # =====================================
            # ACADEMIC
            # =====================================
            "session": (batch.session.name if batch.session else ""),
            "term": (batch.term.name if batch.term else ""),
            # =====================================
            # SUMMARY
            # =====================================
            "summary": {
                "total_score": response.total_score,
                "average_score": response.average_score,
                "position": response.position,
                "passed_subjects": response.passed_subjects,
                "failed_subjects": response.failed_subjects,
                "subjects_offered": len(response.subjects),
            },
            # =====================================
            # SUBJECTS
            # =====================================
            "subjects": [
                {
                    "subject_name": subject.subject_name,
                    "ca_score": subject.ca_score,
                    "exam_score": subject.exam_score,
                    "total_score": subject.total_score,
                    "grade": subject.grade,
                    "remark": subject.remark,
                    "teacher_comment": subject.teacher_comment,
                }
                for subject in response.subjects
            ],
        }

    async def get_approval_history(
        self,
        db,
        batch_id,
        school_id,
    ):
        batch = await self.repo.get_batch(
            db,
            batch_id,
            school_id,
        )

        if not batch:
            raise HTTPException(
                status_code=404,
                detail="Result batch not found.",
            )

        history = await self.repo.get_approval_history(
            db,
            batch_id,
        )

        return ResultMapper.approval_history(
            history,
        )

    async def update_results(
        self,
        db,
        batch_id,
        payload,
        teacher,
    ):
        can_manage = await self.assignment_repo.teacher_has_class_access(
            db,
            teacher.id,
            payload.class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this class.",
            )

        batch = await self.repo.get_batch(
            db=db,
            batch_id=batch_id,
            school_id=teacher.school_id,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="Result batch not found.",
            )

        if batch.status not in (
            "DRAFT",
            "REJECTED",
        ):
            raise HTTPException(
                status_code=400,
                detail="This batch can no longer be edited.",
            )

        committed = False

        try:
            updated_batch, _ = await self._save_batch(
                db=db,
                payload=payload,
                teacher=teacher,
                status="DRAFT",
            )

            await self.repo.commit(db)

            committed = True

            return ResultSubmissionResponse(
                batch_id=updated_batch.id,
                created=False,
                status=updated_batch.status,
                message="Result draft updated successfully.",
            )

        finally:
            if not committed:
                await self.repo.rollback(db)

    async def view_batch(
        self,
        db,
        batch_id,
        teacher,
    ):
        batch = await self.repo.get_batch_details(
            db=db,
            batch_id=batch_id,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="Result batch not found.",
            )

        can_manage = await self.assignment_repo.teacher_has_class_access(
            db,
            teacher.id,
            batch.class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this class.",
            )

        return ResultMapper.class_result(batch)


result_service = ResultService()
