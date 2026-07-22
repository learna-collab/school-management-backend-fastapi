from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cbt_answer import CBTAnswer
from app.models.cbt_attempt import CBTAttempt
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
    ExamApiResponse,
    ExamListApiResponse,
    ExamListResponse,
    ExamResponse,
    QuestionApiResponse,
    QuestionCreate,
    QuestionResponse,
    SubmitAnswerRequest,
)


class CBTService:
    def __init__(self):
        self.repo = CBTRepository()
        self.da = DashboardRepository()

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
            starts_at=payload.start_time,
            ends_at=payload.end_time,
        )

        exam = await self.repo.create_exam(
            db,
            exam,
        )

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

        exam.starts_at = payload.starts_at
        exam.ends_at = payload.ends_at

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
        class_id: UUID,
    ) -> ExamListApiResponse:
        exams = await self.repo.get_class_exams(
            db,
            class_id,
        )

        return ExamListApiResponse(
            success=True,
            message="Available exams retrieved successfully.",
            data=ExamListResponse(
                exams=[ExamResponse.model_validate(exam) for exam in exams],
                count=len(exams),
            ),
        )

    async def start_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ) -> AttemptApiResponse:
        exam = await self.repo.get_exam(
            db,
            exam_id,
        )

        if not exam:
            return AttemptApiResponse(
                success=False,
                message="Exam not found.",
                data=None,
            )

        if not exam.is_published:
            return AttemptApiResponse(
                success=False,
                message="Exam is not available.",
                data=None,
            )

        now = datetime.utcnow()

        if now < exam.start_time:
            return AttemptApiResponse(
                success=False,
                message="Exam has not started.",
                data=None,
            )

        if now > exam.end_time:
            return AttemptApiResponse(
                success=False,
                message="Exam has ended.",
                data=None,
            )

        existing = await self.repo.get_student_attempt(
            db,
            exam_id,
            student_id,
        )

        if existing:
            return AttemptApiResponse(
                success=False,
                message="You have already started this exam.",
                data=AttemptResponse.model_validate(existing),
            )

        attempt = CBTAttempt(
            exam_id=exam.id,
            student_id=student_id,
            started_at=now,
        )

        attempt = await self.repo.create_attempt(
            db,
            attempt,
        )

        return AttemptApiResponse(
            success=True,
            message="Exam started successfully.",
            data=AttemptResponse.model_validate(attempt),
        )

    async def submit_answer(
        self,
        db: AsyncSession,
        payload: SubmitAnswerRequest,
    ) -> AnswerApiResponse:
        attempt = await self.repo.get_attempt(
            db,
            payload.attempt_id,
        )

        if not attempt:
            return AnswerApiResponse(
                success=False,
                message="Attempt not found.",
                data=None,
            )

        if attempt.completed_at:
            return AnswerApiResponse(
                success=False,
                message="Exam has already been submitted.",
                data=None,
            )

        existing = await self.repo.get_answer(
            db,
            payload.attempt_id,
            payload.question_id,
        )

        if existing:
            existing.option_id = payload.option_id

            updated = await self.repo.update_answer(
                db,
                existing,
            )

            return AnswerApiResponse(
                success=True,
                message="Answer updated successfully.",
                data=AnswerResponse.model_validate(updated),
            )

        answer = CBTAnswer(
            attempt_id=payload.attempt_id,
            question_id=payload.question_id,
            option_id=payload.option_id,
        )

        answer = await self.repo.create_answer(
            db,
            answer,
        )

        return AnswerApiResponse(
            success=True,
            message="Answer submitted successfully.",
            data=AnswerResponse.model_validate(answer),
        )

    async def submit_exam(
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

        if attempt.completed_at:
            return AttemptApiResponse(
                success=True,
                message="Exam already submitted.",
                data=AttemptResponse.model_validate(attempt),
            )

        answers = await self.repo.get_attempt_answers(
            db,
            attempt_id,
        )

        score = 0

        for answer in answers:
            if answer.option.is_correct:
                score += answer.question.marks

        exam = await self.repo.get_exam(
            db,
            attempt.exam_id,
        )

        percentage = 0.0

        if exam.total_marks:
            percentage = round(
                score / exam.total_marks * 100,
                2,
            )

        attempt.score = score
        attempt.percentage = percentage
        attempt.passed = percentage >= 50
        attempt.completed_at = datetime.utcnow()

        attempt = await self.repo.submit_attempt(
            db,
            attempt,
        )

        return AttemptApiResponse(
            success=True,
            message="Exam submitted successfully.",
            data=AttemptResponse.model_validate(attempt),
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

        return AttemptListApiResponse(
            success=True,
            message="Exam results retrieved successfully.",
            data=AttemptListResponse(
                attempts=[
                    AttemptResponse.model_validate(
                        attempt,
                    )
                    for attempt in attempts
                ],
                count=len(attempts),
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
        attempt_id: UUID,
        student_id: UUID,
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

        if attempt.student_id != student_id:
            return AttemptApiResponse(
                success=False,
                message="Unauthorized.",
                data=None,
            )

        if attempt.completed_at:
            return AttemptApiResponse(
                success=False,
                message="This exam has already been submitted.",
                data=None,
            )

        return AttemptApiResponse(
            success=True,
            message="Exam resumed successfully.",
            data=AttemptResponse.model_validate(attempt),
        )

    async def get_student_result(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        student_id: UUID,
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

        if attempt.student_id != student_id:
            return AttemptApiResponse(
                success=False,
                message="Unauthorized.",
                data=None,
            )

        if not attempt.completed_at:
            return AttemptApiResponse(
                success=False,
                message="Exam has not been submitted.",
                data=None,
            )

        return AttemptApiResponse(
            success=True,
            message="Result retrieved successfully.",
            data=AttemptResponse.model_validate(attempt),
        )

    async def get_student_history(
        self,
        db: AsyncSession,
        student_id: UUID,
    ) -> AttemptListApiResponse:
        attempts = await self.repo.get_student_attempt_history(
            db,
            student_id,
        )

        return AttemptListApiResponse(
            success=True,
            message="History retrieved successfully.",
            data=AttemptListResponse(
                attempts=[
                    AttemptResponse.model_validate(
                        attempt,
                    )
                    for attempt in attempts
                ],
                count=len(attempts),
            ),
        )
