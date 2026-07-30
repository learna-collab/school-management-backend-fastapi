from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cbt_answer import CBTAnswer
from app.models.cbt_attempt import AttemptStatus, CBTAttempt
from app.models.cbt_exam import CBTExam
from app.models.cbt_question import CBTQuestion
from app.models.cbt_question_option import CBTQuestionOption
from app.models.user import User
from app.repositories.cbt_repository import CBTRepository
from app.repositories.dashboard_repository import (
    DashboardRepository,
)
from app.schemas.cbt import (
    AnswerApiResponse,
    AnswerResponse,
    AttemptApiResponse,
    AttemptListApiResponse,
    AttemptListResponse,
    AttemptResponse,
    CBTApiResponse,
    CBTExamCreate,
    CBTResultsDashboardApiResponse,
    CBTResultsDashboardItem,
    CBTResultsDashboardResponse,
    CBTResultsDashboardStats,
    ExamApiResponse,
    ExamAttemptStatus,
    ExamListApiResponse,
    ExamListResponse,
    ExamResponse,
    ExamSummaryResponse,
    QuestionApiResponse,
    QuestionCreate,
    QuestionResponse,
    StudentExamAttemptApiResponse,
    StudentExamAttemptResponse,
    StudentExamListApiResponse,
    StudentExamListResponse,
    StudentExamResponse,
    StudentExamResultApiResponse,
    StudentExamResultResponse,
    StudentHistoryApiResponse,
    StudentHistoryItem,
    StudentHistoryResponse,
    StudentQuestionOptionResponse,
    StudentQuestionResponse,
    StudentResultApiResponse,
    StudentResultResponse,
    SubmitAnswerRequest,
)


class CBTService:
    def __init__(self):
        self.repo = CBTRepository()
        self.da = DashboardRepository()

    def build_student_exam_response(
        self,
        attempt: CBTAttempt,
    ):
        exam = attempt.exam

        expires_at = attempt.started_at + timedelta(
            minutes=exam.duration_minutes,
        )

        remaining_seconds = max(
            0,
            int((expires_at - datetime.now(UTC)).total_seconds()),
        )

        # Build once
        answer_map = {answer.question_id: answer for answer in attempt.answers}

        questions: list[StudentQuestionResponse] = []

        for question in exam.questions:
            selected_answer = answer_map.get(question.id)

            options = [
                StudentQuestionOptionResponse(
                    id=option.id,
                    option_label=option.option_label,
                    option_text=option.option_text,
                    option_order=option.option_order,
                )
                for option in question.options
            ]

            questions.append(
                StudentQuestionResponse(
                    id=question.id,
                    question_text=question.question,
                    marks=question.marks,
                    order_no=question.question_order,
                    selected_option_id=(
                        selected_answer.selected_option_id if selected_answer else None
                    ),
                    options=options,
                )
            )

        return StudentExamAttemptResponse(
            attempt_id=attempt.id,
            exam_id=exam.id,
            title=exam.title,
            instructions=exam.instructions,
            duration_minutes=exam.duration_minutes,
            total_marks=exam.total_marks,
            started_at=attempt.started_at,
            completed_at=attempt.submitted_at,
            expires_at=expires_at,
            remaining_seconds=remaining_seconds,
            # Resume support
            current_question_index=attempt.current_question_index,
            questions=questions,
        )

    async def update_current_question(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        student_id: UUID,
        current_question_index: int,
    ):
        attempt = await self.repo.get_attempt(
            db,
            attempt_id,
        )

        if not attempt:
            raise HTTPException(
                status_code=404,
                detail="Attempt not found.",
            )

        if attempt.student_id != student_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized.",
            )

        if attempt.submitted_at:
            raise HTTPException(
                status_code=400,
                detail="Exam already submitted.",
            )

        await self.repo.update_current_question(
            db,
            attempt_id,
            current_question_index,
        )

        return {
            "success": True,
            "message": "Current question updated.",
        }

    async def create_exam(
        self,
        db: AsyncSession,
        school_id: UUID,
        user: User,
        payload: CBTExamCreate,
    ) -> ExamApiResponse:
        session = await self.da.get_active_session(db, school_id=user.school_id)
        term = await self.da.get_active_term(db, school_id=user.school_id)
        exam = CBTExam(
            session_id=session.id,
            term_id=term.id,
            school_id=school_id,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            title=payload.title,
            instructions=payload.instructions,
            duration_minutes=payload.duration_minutes,
            total_marks=payload.total_marks,
            # starts_at=payload.starts_at,
            # ends_at=payload.ends_at,
        )

        exam = await self.repo.create_exam(
            db,
            exam,
        )
        exam = await self.repo.get_exam(db, exam.id)

        return ExamApiResponse(
            success=True,
            message="Exam created successfully.",
            data=ExamResponse.model_validate(exam),
        )

    async def update_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
        school_id: UUID,
        payload: CBTExamCreate,
    ):
        exam = await self.repo.get_exam_by_id(
            db=db,
            exam_id=exam_id,
        )

        if not exam:
            raise ValueError("Examination not found.")

        if exam.school_id != school_id:
            raise ValueError("You cannot modify this examination.")

        if exam.is_published:
            raise ValueError("Published examinations cannot be edited.")

        exam.class_id = payload.class_id
        exam.subject_id = payload.subject_id

        exam.title = payload.title
        exam.instructions = payload.instructions

        exam.duration_minutes = payload.duration_minutes
        exam.total_marks = payload.total_marks

        # starts_at and ends_at are intentionally not updated.
        # Every student's timer starts when they begin the exam.

        await db.commit()
        await db.refresh(exam)

        return {
            "success": True,
            "message": "Examination updated successfully.",
            "data": ExamResponse.model_validate(exam),
        }

    async def add_question(
        self,
        db: AsyncSession,
        exam_id: UUID,
        payload: QuestionCreate,
    ) -> QuestionApiResponse:
        question = CBTQuestion(
            exam_id=exam_id,
            question=payload.question_text,
            marks=payload.marks,
            question_order=payload.order_no,
        )

        question = await self.repo.create_question(db, question)

        for index, option in enumerate(payload.options):
            option_model = CBTQuestionOption(
                question_id=question.id,
                option_label=chr(65 + index),  # A, B, C, D...
                option_text=option.option_text,
                option_order=index + 1,
                is_correct=option.is_correct,
            )

            await self.repo.create_option(db, option_model)

        question = await self.repo.get_question(db, question.id)

        return QuestionApiResponse(
            success=True,
            message="Question added successfully.",
            data=question,
        )

    async def publish_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ) -> CBTApiResponse:
        exam = await self.repo.publish_exam(
            db,
            exam_id,
        )

        if not exam:
            return CBTApiResponse(
                success=False,
                message="Exam not found.",
            )

        return CBTApiResponse(
            success=True,
            message="Exam published successfully.",
        )

    async def get_available_exams(
        self,
        db: AsyncSession,
        user: User,
    ):
        current_enrollment = next(
            (enrollment for enrollment in user.enrollments if enrollment.is_current),
            None,
        )

        if current_enrollment is None:
            return StudentExamListApiResponse(
                success=True,
                message="No available examinations.",
                data=StudentExamListResponse(
                    exams=[],
                    count=0,
                ),
            )

        exams = await self.repo.get_student_available_exams(
            db=db,
            class_id=current_enrollment.class_id,
            student_id=user.id,
        )

        responses: list[StudentExamResponse] = []

        for item in exams:
            exam: CBTExam = item["exam"]
            attempt: CBTAttempt | None = item["attempt"]

            if attempt is None:
                status = ExamAttemptStatus.NOT_STARTED
                attempt_id = None

            elif attempt.submitted_at is not None:
                status = ExamAttemptStatus.COMPLETED
                attempt_id = attempt.id

            else:
                status = ExamAttemptStatus.IN_PROGRESS
                attempt_id = attempt.id

            responses.append(
                StudentExamResponse(
                    id=exam.id,
                    title=exam.title,
                    instructions=exam.instructions,
                    duration_minutes=exam.duration_minutes,
                    total_marks=exam.total_marks,
                    subject_name=exam.subject.name,
                    class_name=exam.school_class.name,
                    question_count=len(exam.questions),
                    attempt_status=status,
                    attempt_id=attempt_id,
                )
            )

        return StudentExamListApiResponse(
            success=True,
            message="Available examinations retrieved successfully.",
            data=StudentExamListResponse(
                exams=responses,
                count=len(responses),
            ),
        )

    async def start_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ):
        exam = await self.repo.get_exam_for_student(
            db,
            exam_id,
        )

        if not exam:
            return StudentExamAttemptApiResponse(
                success=False,
                message="Exam not found.",
                data=None,
            )

        if not exam.is_published:
            return StudentExamAttemptApiResponse(
                success=False,
                message="Exam is not available.",
                data=None,
            )

        now = datetime.now(UTC)

        existing = await self.repo.get_student_exam_attempt(
            db,
            exam_id,
            student_id,
        )

        # -----------------------------------------------------
        # Existing attempt (idempotent)
        # -----------------------------------------------------

        if existing:
            # Already submitted
            if existing.submitted_at is not None:
                return StudentExamAttemptApiResponse(
                    success=False,
                    message="You already completed this exam.",
                    data=None,
                )

            # Time elapsed since exam started
            elapsed_seconds = int((now - existing.started_at).total_seconds())

            allowed_seconds = exam.duration_minutes * 60

            # Time has expired -> auto submit
            if elapsed_seconds >= allowed_seconds:
                await self.submit_exam(
                    db=db,
                    attempt_id=existing.id,
                    student_id=student_id,
                )

                return StudentExamAttemptApiResponse(
                    success=False,
                    message="Your examination time has elapsed and your exam has been submitted.",
                    data=None,
                )

            existing = await self.repo.get_student_attempt_details(
                db,
                existing.id,
            )

            return StudentExamAttemptApiResponse(
                success=True,
                message="Exam resumed.",
                data=self.build_student_exam_response(existing),
            )

        # -----------------------------------------------------
        # First attempt
        # -----------------------------------------------------

        attempt = CBTAttempt(
            school_id=exam.school_id,
            exam_id=exam.id,
            student_id=student_id,
            started_at=now,
            score=0,
            total_marks=exam.total_marks,
            percentage=0,
            status=AttemptStatus.IN_PROGRESS,
            is_passed=False,
        )

        attempt = await self.repo.create_attempt(
            db,
            attempt,
        )

        attempt = await self.repo.get_student_attempt_details(
            db,
            attempt.id,
        )

        return StudentExamAttemptApiResponse(
            success=True,
            message="Exam started successfully.",
            data=self.build_student_exam_response(attempt),
        )

    async def submit_answer(
        self,
        db: AsyncSession,
        payload: SubmitAnswerRequest,
        student_id: UUID,
    ):
        attempt = await self.repo.get_student_attempt_details(
            db,
            payload.attempt_id,
        )

        if not attempt:
            return AnswerApiResponse(
                success=False,
                message="Attempt not found.",
                data=None,
            )

        # ---------------------------------------------------------
        # SECURITY 1: Ensure owner
        # ---------------------------------------------------------

        if attempt.student_id != student_id:
            return AnswerApiResponse(
                success=False,
                message="Unauthorized attempt.",
                data=None,
            )

        # ---------------------------------------------------------
        # SECURITY 2: Already submitted
        # ---------------------------------------------------------

        if attempt.submitted_at is not None:
            return AnswerApiResponse(
                success=False,
                message="Exam already submitted.",
                data=None,
            )

        exam = attempt.exam

        # ---------------------------------------------------------
        # SECURITY 3: Student timer
        # ---------------------------------------------------------

        now = datetime.now(UTC)

        expires_at = attempt.started_at + timedelta(
            minutes=exam.duration_minutes,
        )

        if now >= expires_at:
            await self.submit_exam(
                db=db,
                attempt_id=attempt.id,
                student_id=student_id,
            )

            return AnswerApiResponse(
                success=False,
                message="Time has elapsed. Your examination has been submitted.",
                data=None,
            )

        # ---------------------------------------------------------
        # SECURITY 4: Question belongs to exam
        # ---------------------------------------------------------

        question = await self.repo.get_question(
            db,
            payload.question_id,
        )

        if not question:
            return AnswerApiResponse(
                success=False,
                message="Question not found.",
                data=None,
            )

        if question.exam_id != attempt.exam_id:
            return AnswerApiResponse(
                success=False,
                message="Question does not belong to this examination.",
                data=None,
            )

        # ---------------------------------------------------------
        # SECURITY 5: Option belongs to question
        # ---------------------------------------------------------

        option = await self.repo.get_option(
            db,
            payload.option_id,
        )

        if not option:
            return AnswerApiResponse(
                success=False,
                message="Option not found.",
                data=None,
            )

        if option.question_id != question.id:
            return AnswerApiResponse(
                success=False,
                message="Option does not belong to this question.",
                data=None,
            )

        # ---------------------------------------------------------
        # UPSERT ANSWER
        # ---------------------------------------------------------

        existing = await self.repo.get_answer(
            db,
            payload.attempt_id,
            payload.question_id,
        )

        if existing:
            existing.selected_option_id = payload.option_id

            updated = await self.repo.update_answer(
                db,
                existing,
            )

            return AnswerApiResponse(
                success=True,
                message="Answer updated.",
                data=AnswerResponse.model_validate(updated),
            )

        answer = CBTAnswer(
            attempt_id=payload.attempt_id,
            question_id=payload.question_id,
            selected_option_id=payload.option_id,
        )

        answer = await self.repo.create_answer(
            db,
            answer,
        )

        return AnswerApiResponse(
            success=True,
            message="Answer saved.",
            data=AnswerResponse.model_validate(answer),
        )

    async def get_school_exams(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> ExamListApiResponse:
        exams = await self.repo.get_school_exams(
            db,
            school_id,
        )

        return ExamListApiResponse(
            success=True,
            message="Exams retrieved successfully.",
            data=ExamListResponse(
                exams=[ExamResponse.model_validate(exam) for exam in exams],
                count=len(exams),
            ),
        )

    async def get_exam_details(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ) -> ExamApiResponse:
        exam = await self.repo.get_exam(
            db,
            exam_id,
        )

        if not exam:
            return ExamApiResponse(
                success=False,
                message="Exam not found.",
                data=None,
            )

        return ExamApiResponse(
            success=True,
            message="Exam retrieved successfully.",
            data=ExamResponse.model_validate(exam),
        )

    async def update_question(
        self,
        db: AsyncSession,
        question_id: UUID,
        payload: QuestionCreate,
    ) -> QuestionApiResponse:
        question = await self.repo.get_question(
            db,
            question_id,
        )

        if not question:
            return QuestionApiResponse(
                success=False,
                message="Question not found.",
                data=None,
            )

        # update question fields
        question.question = payload.question_text
        question.marks = payload.marks
        question.question_order = payload.order_no

        # remove old options
        await self.repo.delete_question_options(
            db,
            question.id,
        )

        # recreate options
        for index, option in enumerate(payload.options):
            new_option = CBTQuestionOption(
                question_id=question.id,
                option_label=chr(65 + index),  # A,B,C,D
                option_text=option.option_text,
                option_order=index + 1,
                is_correct=option.is_correct,
            )

            db.add(new_option)

        await db.commit()

        updated_question = await self.repo.get_question(
            db,
            question.id,
        )

        return QuestionApiResponse(
            success=True,
            message="Question updated successfully.",
            data=QuestionResponse.model_validate(updated_question),
        )

    async def delete_question(
        self,
        db: AsyncSession,
        question_id: UUID,
    ) -> CBTApiResponse:
        question = await self.repo.get_question(
            db,
            question_id,
        )

        if not question:
            return CBTApiResponse(
                success=False,
                message="Question not found.",
            )

        await self.repo.delete_question(
            db,
            question,
        )

        return CBTApiResponse(
            success=True,
            message="Question deleted successfully.",
        )

    async def delete_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ) -> CBTApiResponse:
        deleted = await self.repo.delete_exam(
            db,
            exam_id,
        )

        if not deleted:
            return CBTApiResponse(
                success=False,
                message="Exam not found.",
            )

        return CBTApiResponse(
            success=True,
            message="Exam deleted successfully.",
        )

    async def get_exam_results(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ) -> AttemptListApiResponse:
        attempts = await self.repo.get_exam_attempts(
            db,
            exam_id,
        )

        if not attempts:
            exam = await self.repo.get_exam(
                db,
                exam_id,
            )

            if not exam:
                raise HTTPException(
                    status_code=404,
                    detail="Exam not found.",
                )

            return AttemptListApiResponse(
                success=True,
                message="Exam results retrieved successfully.",
                data=AttemptListResponse(
                    exam=ExamSummaryResponse(
                        id=exam.id,
                        title=exam.title,
                        duration_minutes=exam.duration_minutes,
                        total_marks=exam.total_marks,
                        starts_at=exam.starts_at,
                        ends_at=exam.ends_at,
                        is_published=exam.is_published,
                        question_count=len(exam.questions),
                        class_name=exam.school_class.name,
                        subject_name=exam.subject.name,
                    ),
                    attempts=[],
                    count=0,
                    average_score=0,
                    highest_score=0,
                    lowest_score=0,
                    passed_count=0,
                    failed_count=0,
                ),
            )

        exam = attempts[0].exam

        scores = [a.score for a in attempts]

        return AttemptListApiResponse(
            success=True,
            message="Exam results retrieved successfully.",
            data=AttemptListResponse(
                exam=ExamSummaryResponse(
                    id=exam.id,
                    title=exam.title,
                    duration_minutes=exam.duration_minutes,
                    total_marks=exam.total_marks,
                    starts_at=exam.starts_at,
                    ends_at=exam.ends_at,
                    is_published=exam.is_published,
                    question_count=len(exam.questions),
                    class_name=exam.school_class.name,
                    subject_name=exam.subject.name,
                ),
                attempts=[AttemptResponse.model_validate(a) for a in attempts],
                count=len(attempts),
                average_score=round(sum(scores) / len(scores), 2),
                highest_score=max(scores),
                lowest_score=min(scores),
                passed_count=sum(1 for a in attempts if a.is_passed),
                failed_count=sum(1 for a in attempts if not a.is_passed),
            ),
        )

    async def get_attempt(
        self,
        db: AsyncSession,
        attempt_id: UUID,
    ) -> AttemptApiResponse:
        attempt = await self.repo.get_attempt(
            db,
            attempt_id,
        )

        if not attempt:
            return AttemptApiResponse(
                success=False,
                message="Attempt not found.",
                data=None,
            )

        return AttemptApiResponse(
            success=True,
            message="Attempt retrieved successfully.",
            data=AttemptResponse.model_validate(attempt),
        )

    # =====================================================
    # STUDENT
    # =====================================================

    async def resume_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ):
        attempt = await self.repo.get_active_student_attempt(
            db=db,
            exam_id=exam_id,
            student_id=student_id,
        )

        if attempt is None:
            return StudentExamAttemptApiResponse(
                success=False,
                message="Attempt not found.",
                data=None,
            )

        if attempt.submitted_at is not None:
            return StudentExamAttemptApiResponse(
                success=False,
                message="Exam already submitted.",
                data=None,
            )

        return StudentExamAttemptApiResponse(
            success=True,
            message="Exam resumed successfully.",
            data=self.build_student_exam_response(attempt),
        )

    async def get_student_result(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        student_id: UUID,
    ):
        attempt = await self.repo.get_student_attempt_details(
            db,
            attempt_id,
        )

        if not attempt:
            return StudentResultApiResponse(
                success=False,
                message="Result not found.",
                data=None,
            )

        if attempt.student_id != student_id:
            return StudentResultApiResponse(
                success=False,
                message="Unauthorized.",
                data=None,
            )

        if not attempt.submitted_at:
            return StudentResultApiResponse(
                success=False,
                message="Exam not completed.",
                data=None,
            )

        answers = await self.repo.get_attempt_answers(
            db,
            attempt_id,
        )
        exam = attempt.exam
        answers_map = {answer.question_id: answer for answer in answers}

        correct = 0
        wrong = 0
        unanswered = 0

        for question in exam.questions:
            answer = answers_map.get(question.id)

            if answer is None:
                unanswered += 1
            elif answer.selected_option.is_correct:
                correct += 1
            else:
                wrong += 1
        print(attempt.is_passed)
        return StudentResultApiResponse(
            success=True,
            message="Result retrieved successfully.",
            data=StudentResultResponse(
                attempt_id=attempt.id,
                exam_id=exam.id,
                exam_title=exam.title,
                subject_name=exam.subject.name,
                total_marks=exam.total_marks,
                score=attempt.score,
                percentage=attempt.percentage,
                passed=attempt.is_passed,
                total_questions=len(exam.questions),
                answered_questions=correct + wrong,
                correct_answers=correct,
                wrong_answers=wrong,
                started_at=attempt.started_at,
                completed_at=attempt.submitted_at,
            ),
        )

    async def get_student_history(
        self,
        db: AsyncSession,
        student_id: UUID,
    ):
        attempts = await self.repo.get_student_attempt_history(
            db,
            student_id,
        )

        history = []

        for attempt in attempts:
            history.append(
                StudentHistoryItem(
                    attempt_id=attempt.id,
                    exam_id=attempt.exam.id,
                    exam_title=attempt.exam.title,
                    subject_name=attempt.exam.subject.name,
                    score=attempt.score,
                    percentage=attempt.percentage,
                    passed=attempt.is_passed,
                    completed_at=attempt.submitted_at,
                )
            )

        return StudentHistoryApiResponse(
            success=True,
            message="History retrieved successfully.",
            data=StudentHistoryResponse(
                attempts=history,
                count=len(history),
            ),
        )

    async def get_results_dashboard(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> CBTResultsDashboardApiResponse:
        """
        Returns the CBT results dashboard for a school.

        One row represents one examination.
        """
        dashboard_rows = await self.repo.get_results_dashboard(
            db=db,
            school_id=school_id,
        )

        dashboard_stats = await self.repo.get_results_dashboard_stats(
            db=db,
            school_id=school_id,
        )

        results = [
            CBTResultsDashboardItem(
                exam_id=row["exam_id"],
                title=row["title"],
                class_name=row["class_name"],
                subject_name=row["subject_name"],
                attempts=row["attempts"],
                average_score=round(
                    float(row["average_score"]),
                    2,
                ),
                average_percentage=round(
                    float(row["average_percentage"]),
                    2,
                ),
                highest_score=round(float(row["highest_score"]), 2),
                lowest_score=round(float(row["lowest_score"]), 2),
                pass_rate=round(
                    float(row["pass_rate"]),
                    2,
                ),
                total_marks=row["total_marks"],
                published=row["is_published"],
                starts_at=row["starts_at"],
                ends_at=row["ends_at"],
            )
            for row in dashboard_rows
        ]

        stats = CBTResultsDashboardStats(
            total_exams=dashboard_stats["total_exams"],
            total_attempts=dashboard_stats["total_attempts"],
            average_percentage=round(
                float(dashboard_stats["average_percentage"]),
                2,
            ),
            overall_pass_rate=round(
                float(dashboard_stats["overall_pass_rate"]),
                2,
            ),
        )

        return CBTResultsDashboardApiResponse(
            success=True,
            message="CBT results dashboard retrieved successfully.",
            data=CBTResultsDashboardResponse(
                results=results,
                count=len(results),
                stats=stats,
            ),
        )

    async def submit_exam(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        student_id: UUID,
    ):
        attempt = await self.repo.get_student_attempt_details(
            db,
            attempt_id,
        )

        if not attempt:
            return StudentExamResultApiResponse(
                success=False,
                message="Attempt not found.",
                data=None,
            )

        if attempt.student_id != student_id:
            return StudentExamResultApiResponse(
                success=False,
                message="Unauthorized attempt.",
                data=None,
            )

        # Idempotency
        if attempt.submitted_at is not None:
            return StudentExamResultApiResponse(
                success=False,
                message="Exam has already been submitted.",
                data=None,
            )

        exam = attempt.exam

        # =====================================================
        # SERVER TIMER (SOURCE OF TRUTH)
        # =====================================================

        now = datetime.now(UTC)

        expires_at = attempt.started_at + timedelta(
            minutes=exam.duration_minutes,
        )

        completed_at = min(now, expires_at)

        duration_taken = int((completed_at - attempt.started_at).total_seconds())

        # =====================================================
        # LOAD ANSWERS
        # =====================================================

        answers = await self.repo.get_attempt_answers(
            db,
            attempt_id,
        )

        answer_map = {answer.question_id: answer for answer in answers}

        correct = 0
        wrong = 0
        unanswered = 0
        score = 0

        for question in exam.questions:
            answer = answer_map.get(question.id)

            if answer is None:
                unanswered += 1
                continue

            if answer.selected_option.is_correct:
                correct += 1
                score += question.marks
            else:
                wrong += 1

        # =====================================================
        # SCORE
        # =====================================================

        total_marks = exam.total_marks

        percentage = round((score / total_marks) * 100, 2) if total_marks > 0 else 0

        pass_mark = getattr(exam, "pass_mark", 50)

        is_passed = percentage >= pass_mark

        # =====================================================
        # UPDATE ATTEMPT
        # =====================================================

        attempt.score = score
        attempt.percentage = percentage
        attempt.is_passed = is_passed
        attempt.status = AttemptStatus.SUBMITTED

        attempt.submitted_at = completed_at
        attempt.duration_taken = duration_taken

        await self.repo.submit_attempt(
            db,
            attempt,
        )

        # =====================================================
        # RESPONSE
        # =====================================================

        return StudentExamResultApiResponse(
            success=True,
            message="Exam submitted successfully.",
            data=StudentExamResultResponse(
                attempt_id=attempt.id,
                exam_id=exam.id,
                title=exam.title,
                score=score,
                total_marks=total_marks,
                percentage=percentage,
                passed=is_passed,
                correct_answers=correct,
                wrong_answers=wrong,
                unanswered_questions=unanswered,
                answered_questions=correct + wrong,
                total_questions=len(exam.questions),
                completed_at=completed_at,
            ),
        )
