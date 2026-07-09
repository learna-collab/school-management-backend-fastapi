from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.assignment_r import AssignmentRepository
from app.schemas.assignments import (
    AssignedSubject,
    AssignedTeacher,
    AssignmentSetupResponse,
    AssignmentSummaryResponse,
    ClassAssignmentResponse,
    ClassOption,
    CreateClassAssignmentsRequest,
    SubjectOption,
    TeacherOption,
    UpdateClassAssignmentsRequest,
)


class AssignmentService:
    def __init__(self):
        self.repository = AssignmentRepository()

        # =====================================================

    # CLASS VALIDATION
    # =====================================================

    async def _validate_class(
        self,
        db: AsyncSession,
        class_id: UUID,
        school_id: UUID,
    ):
        school_class = await self.repository.get_class(
            db=db,
            class_id=class_id,
            school_id=school_id,
        )

        if school_class is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found.",
            )

        return school_class

    # =====================================================
    # DUPLICATE SUBJECTS
    # =====================================================

    def _check_duplicate_subjects(
        self,
        payload: CreateClassAssignmentsRequest | UpdateClassAssignmentsRequest,
    ):
        seen = set()

        for item in payload.assignments:
            if item.subject_id in seen:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Duplicate subject detected in request.",
                )

            seen.add(item.subject_id)

    # =====================================================
    # GET SETUP
    # =====================================================

    async def get_setup(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> AssignmentSetupResponse:
        classes = await self.repository.get_classes(
            db=db,
            school_id=current_user.school_id,
        )

        subjects = await self.repository.get_subjects(
            db=db,
        )

        teachers = await self.repository.get_teachers(
            db=db,
            school_id=current_user.school_id,
        )

        return AssignmentSetupResponse(
            classes=[ClassOption.model_validate(c) for c in classes],
            subjects=[SubjectOption.model_validate(s) for s in subjects],
            teachers=[TeacherOption.model_validate(t) for t in teachers],
        )

    # =====================================================
    # CREATE CLASS ASSIGNMENTS
    # BULK + PARTIAL SUCCESS
    # =====================================================

    async def create_assignments(
        self,
        db: AsyncSession,
        payload: CreateClassAssignmentsRequest,
        current_user: User,
    ) -> AssignmentSummaryResponse:
        school_id = current_user.school_id

        # ---------------------------------------------
        # Validate class
        # ---------------------------------------------

        await self._validate_class(
            db=db,
            class_id=payload.class_id,
            school_id=school_id,
        )

        # ---------------------------------------------
        # Validate payload
        # ---------------------------------------------

        if not payload.assignments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No assignments provided.",
            )

        # Prevent duplicate subjects
        self._check_duplicate_subjects(payload)

        try:
            # =================================================
            # COLLECT IDS
            # =================================================

            subject_ids = [item.subject_id for item in payload.assignments]

            teacher_ids = [item.teacher_id for item in payload.assignments]

            # =================================================
            # BULK FETCH SUBJECTS
            # =================================================

            subjects = await self.repository.get_subjects_by_ids(
                db=db,
                subject_ids=subject_ids,
            )

            subjects_map = {subject.id: subject for subject in subjects}

            # =================================================
            # BULK FETCH TEACHERS
            # =================================================

            teachers = await self.repository.get_teachers_by_ids(
                db=db,
                school_id=school_id,
                teacher_ids=teacher_ids,
            )

            teachers_map = {teacher.id: teacher for teacher in teachers}

            # =================================================
            # FETCH EXISTING ASSIGNMENTS
            # =================================================

            existing_assignments = await self.repository.get_existing_assignments(
                db=db,
                class_id=payload.class_id,
                school_id=school_id,
            )

            existing_map = {
                assignment.subject_id: assignment for assignment in existing_assignments
            }

            # =================================================
            # COUNTERS
            # =================================================

            created = 0
            updated = 0
            skipped = 0

            created_subjects = []
            updated_subjects = []
            skipped_subjects = []
            # =================================================
            # PROCESS ASSIGNMENTS
            # =================================================

            for item in payload.assignments:
                subject = subjects_map.get(item.subject_id)

                teacher = teachers_map.get(item.teacher_id)

                # -----------------------------------------
                # Subject does not exist
                # -----------------------------------------

                if not subject:
                    skipped += 1

                    skipped_subjects.append(str(item.subject_id))

                    continue

                # -----------------------------------------
                # Teacher does not exist
                # -----------------------------------------

                if not teacher:
                    skipped += 1

                    skipped_subjects.append(subject.name)

                    continue

                existing = existing_map.get(item.subject_id)

                # -----------------------------------------
                # Already assigned to same teacher
                # -----------------------------------------

                if existing and existing.teacher_id == item.teacher_id:
                    skipped += 1

                    skipped_subjects.append(subject.name)

                    continue

                # -----------------------------------------
                # Existing assignment but teacher changed
                # -----------------------------------------

                if existing:
                    await self.repository.update_teacher_assignment(
                        assignment=existing,
                        teacher_id=item.teacher_id,
                    )

                    updated += 1

                    updated_subjects.append(subject.name)

                    continue

                # -----------------------------------------
                # Create ClassSubject if missing
                # -----------------------------------------

                class_subject_exists = await self.repository.class_subject_exists(
                    db=db,
                    class_id=payload.class_id,
                    subject_id=item.subject_id,
                    school_id=school_id,
                )

                if not class_subject_exists:
                    await self.repository.create_class_subject(
                        db=db,
                        class_id=payload.class_id,
                        subject_id=item.subject_id,
                        school_id=school_id,
                    )

                # -----------------------------------------
                # Create teacher assignment
                # -----------------------------------------

                new_assignment = await self.repository.create_teacher_assignment(
                    db=db,
                    class_id=payload.class_id,
                    subject_id=item.subject_id,
                    teacher_id=item.teacher_id,
                    school_id=school_id,
                )

                created += 1

                created_subjects.append(subject.name)
            # =================================================
            # SAVE TRANSACTION
            # =================================================

            await db.commit()

            return AssignmentSummaryResponse(
                message=("Assignments processed successfully."),
                created=created,
                updated=updated,
                skipped=skipped,
                created_subjects=created_subjects,
                updated_subjects=updated_subjects,
                skipped_subjects=skipped_subjects,
            )

        except HTTPException:
            await db.rollback()

            raise

        except Exception:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=("Unable to process assignments."),
            )

    # =====================================================
    # GET CLASS ASSIGNMENTS
    # =====================================================

    async def get_class_assignments(
        self,
        db: AsyncSession,
        class_id: UUID,
        current_user: User,
    ) -> ClassAssignmentResponse:
        school_id = current_user.school_id

        # ---------------------------------------------
        # Validate class
        # ---------------------------------------------

        school_class = await self._validate_class(
            db=db,
            class_id=class_id,
            school_id=school_id,
        )

        # ---------------------------------------------
        # Fetch assignments
        # ---------------------------------------------

        assignments = await self.repository.get_class_assignments(
            db=db,
            class_id=class_id,
            school_id=school_id,
        )

        response = []

        for assignment in assignments:
            response.append(
                AssignedSubject(
                    assignment_id=assignment.id,
                    subject_id=assignment.subject.id,
                    subject_name=assignment.subject.name,
                    subject_code=assignment.subject.code,
                    teacher=AssignedTeacher(
                        id=assignment.teacher.id,
                        first_name=(assignment.teacher.first_name),
                        last_name=(assignment.teacher.last_name),
                        email=(assignment.teacher.email),
                    ),
                )
            )

        return ClassAssignmentResponse(
            class_id=school_class.id,
            class_name=school_class.name,
            assignments=response,
        )

    # =====================================================
    # UPDATE CLASS ASSIGNMENTS
    # =====================================================

    async def update_assignments(
        self,
        db: AsyncSession,
        class_id: UUID,
        payload: UpdateClassAssignmentsRequest,
        current_user: User,
    ) -> AssignmentSummaryResponse:
        school_id = current_user.school_id

        # ---------------------------------------------
        # Validate class
        # ---------------------------------------------

        await self._validate_class(
            db=db,
            class_id=class_id,
            school_id=school_id,
        )

        if not payload.assignments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No assignments provided.",
            )

        self._check_duplicate_subjects(payload)

        try:
            # =================================================
            # FETCH PAYLOAD DATA
            # =================================================

            subject_ids = [item.subject_id for item in payload.assignments]

            teacher_ids = [item.teacher_id for item in payload.assignments]

            subjects = await self.repository.get_subjects_by_ids(
                db=db,
                subject_ids=subject_ids,
            )

            teachers = await self.repository.get_teachers_by_ids(
                db=db,
                school_id=school_id,
                teacher_ids=teacher_ids,
            )

            existing_assignments = await self.repository.get_existing_assignments(
                db=db,
                class_id=class_id,
                school_id=school_id,
            )

            subjects_map = {subject.id: subject for subject in subjects}

            teachers_map = {teacher.id: teacher for teacher in teachers}

            existing_map = {
                assignment.subject_id: assignment for assignment in existing_assignments
            }

            payload_subject_ids = set(subject_ids)

            created = 0
            updated = 0
            skipped = 0

            created_subjects = []
            updated_subjects = []
            skipped_subjects = []

            # =================================================
            # REMOVE DELETED SUBJECTS
            # =================================================

            existing_subject_ids = set(existing_map.keys())

            removed_subjects = existing_subject_ids - payload_subject_ids

            for subject_id in removed_subjects:
                await self.repository.delete_teacher_assignment_by_subject(
                    db=db,
                    class_id=class_id,
                    subject_id=subject_id,
                    school_id=school_id,
                )

                await self.repository.delete_class_subject_by_subject(
                    db=db,
                    class_id=class_id,
                    subject_id=subject_id,
                    school_id=school_id,
                )
            # =================================================
            # CREATE / UPDATE
            # =================================================

            for item in payload.assignments:
                subject = subjects_map.get(item.subject_id)

                teacher = teachers_map.get(item.teacher_id)

                if not subject or not teacher:
                    skipped += 1

                    continue

                existing = existing_map.get(item.subject_id)

                # -----------------------------------------
                # Existing assignment
                # -----------------------------------------

                if existing:
                    if existing.teacher_id == item.teacher_id:
                        skipped += 1

                        skipped_subjects.append(subject.name)

                        continue

                    await self.repository.update_teacher_assignment(
                        assignment=existing,
                        teacher_id=item.teacher_id,
                    )

                    updated += 1

                    updated_subjects.append(subject.name)

                    continue

                # -----------------------------------------
                # New assignment
                # -----------------------------------------

                exists = await self.repository.class_subject_exists(
                    db=db,
                    class_id=class_id,
                    subject_id=item.subject_id,
                    school_id=school_id,
                )

                if not exists:
                    await self.repository.create_class_subject(
                        db=db,
                        class_id=class_id,
                        subject_id=item.subject_id,
                        school_id=school_id,
                    )

                await self.repository.create_teacher_assignment(
                    db=db,
                    class_id=class_id,
                    subject_id=item.subject_id,
                    teacher_id=item.teacher_id,
                    school_id=school_id,
                )

                created += 1

                created_subjects.append(subject.name)
            await db.commit()

            return AssignmentSummaryResponse(
                message="Assignments updated successfully.",
                created=created,
                updated=updated,
                skipped=skipped,
                created_subjects=created_subjects,
                updated_subjects=updated_subjects,
                skipped_subjects=skipped_subjects,
            )

        except HTTPException:
            await db.rollback()

            raise

        except Exception:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to update assignments.",
            )

    # =====================================================
    # DELETE SINGLE ASSIGNMENT
    # =====================================================

    async def delete_assignment(
        self,
        db: AsyncSession,
        class_id: UUID,
        subject_id: UUID,
        current_user: User,
    ) -> AssignmentSummaryResponse:
        school_id = current_user.school_id

        # ---------------------------------------------
        # Validate class
        # ---------------------------------------------

        await self._validate_class(
            db=db,
            class_id=class_id,
            school_id=school_id,
        )

        try:
            assignment = await self.repository.get_teacher_assignment(
                db=db,
                class_id=class_id,
                subject_id=subject_id,
                school_id=school_id,
            )

            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assignment not found.",
                )

            # ---------------------------------------------
            # Delete teacher assignment
            # ---------------------------------------------

            await self.repository.delete_teacher_assignment_by_subject(
                db=db,
                class_id=class_id,
                subject_id=subject_id,
                school_id=school_id,
            )

            # ---------------------------------------------
            # Delete class subject
            # ---------------------------------------------

            await self.repository.delete_class_subject_by_subject(
                db=db,
                class_id=class_id,
                subject_id=subject_id,
                school_id=school_id,
            )

            await db.commit()

            subject_name = (
                assignment.subject.name if assignment.subject else str(subject_id)
            )

            return AssignmentSummaryResponse(
                message="Assignment deleted successfully.",
                skipped=0,
                created=0,
                updated=0,
                created_subjects=[],
                updated_subjects=[],
                skipped_subjects=[subject_name],
            )

        except HTTPException:
            await db.rollback()

            raise

        except Exception:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to delete assignment.",
            )
