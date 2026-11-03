from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cbt_answer import CBTAnswer
from app.models.cbt_attempt import AttemptStatus, CBTAttempt
from app.models.cbt_exam import AssessmentType, CBTExam
from app.models.cbt_question import CBTQuestion
from app.models.cbt_question_option import CBTQuestionOption
from app.models.result_batch import ResultBatch
from app.models.result_record import ResultRecord
from app.models.user import User
from app.repositories.cbt_repository import CBTRepository
from app.repositories.dashboard_repository import DashboardRepository
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
from app.services.result_service import ResultService


class CBTService:
    def __init__(self):
        self.repo = CBTRepository()
        self.da = DashboardRepository()

    # ===========================================================
    # HELPERS
    # ===========================================================

    @staticmethod
    def _assessment_label(
        assessment_type: AssessmentType,
        assessment_number: int | None,
    ) -> str:
        if assessment_type == AssessmentType.CA:
            return f"CA{assessment_number}"

        return "Main Examination"

    @staticmethod
    def calculate_contribution(
        score: float,
        raw_total_marks: float,
        contribution_marks: float,
    ) -> float:
        """
        Converts a raw CBT score into its allocated academic contribution.

        Examples:
            15/20 with allocation 20 = 15
            30/40 with allocation 20 = 15
        """
        if raw_total_marks <= 0 or contribution_marks <= 0:
            return 0.0

        normalized = (
            max(0.0, min(float(score), float(raw_total_marks))) / float(raw_total_marks)
        ) * float(contribution_marks)

        return round(
            max(
                0.0,
                min(normalized, float(contribution_marks)),
            ),
            2,
        )

    async def _validate_assessment_allocation(
        self,
        db: AsyncSession,
        *,
        school_id: UUID,
        session_id: UUID,
        term_id: UUID,
        payload: CBTExamCreate,
        exclude_exam_id: UUID | None = None,
    ) -> None:
        """
        Enforces the official academic assessment structure:

            CA1 = 20 marks
            CA2 = 20 marks
            Main Examination = 60 marks

        Legacy CBT exams are excluded from allocation calculations.
        """

        if payload.assessment_type == AssessmentType.CA:
            if payload.assessment_number not in (1, 2):
                raise HTTPException(
                    status_code=400,
                    detail="Only CA1 and CA2 are allowed.",
                )

            if payload.contribution_marks != 20:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Each continuous assessment must contribute exactly 20 marks."
                    ),
                )

            allocated = await self.repo.get_assessment_allocation(
                db,
                school_id=school_id,
                session_id=session_id,
                term_id=term_id,
                class_id=payload.class_id,
                subject_id=payload.subject_id,
                assessment_type=AssessmentType.CA.value,
                exclude_exam_id=exclude_exam_id,
            )

            if allocated + 20 > 40:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Both continuous assessment slots have already "
                        "been allocated for this class and subject."
                    ),
                )

        elif payload.assessment_type == AssessmentType.EXAM:
            if payload.assessment_number is not None:
                raise HTTPException(
                    status_code=400,
                    detail=("The main examination cannot have an assessment number."),
                )

            if payload.contribution_marks != 60:
                raise HTTPException(
                    status_code=400,
                    detail=("The main examination must contribute exactly 60 marks."),
                )

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported assessment type.",
            )

    # ===========================================================
    # STUDENT EXAM RESPONSE BUILDER
    # ===========================================================

    def build_student_exam_response(
        self,
        attempt: CBTAttempt,
    ) -> StudentExamAttemptResponse:
        exam = attempt.exam

        expires_at = attempt.started_at + timedelta(
            minutes=exam.duration_minutes,
        )

        remaining_seconds = max(
            0,
            int((expires_at - datetime.now(UTC)).total_seconds()),
        )

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
            # Examination configuration
            duration_minutes=exam.duration_minutes,
            total_marks=exam.total_marks,
            # Assessment configuration
            assessment_type=exam.assessment_type,
            assessment_label=exam.assessment_label,
            contribution_marks=exam.contribution_marks,
            # Attempt configuration
            attempt_number=attempt.attempt_number,
            max_attempts=exam.max_attempts,
            # Timing information
            started_at=attempt.started_at,
            completed_at=attempt.submitted_at,
            expires_at=expires_at,
            remaining_seconds=remaining_seconds,
            current_question_index=attempt.current_question_index,
            # Questions and previously selected answers
            questions=questions,
        )

    # ===========================================================
    # UPDATE CURRENT QUESTION
    # ===========================================================

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

        if current_question_index < 0:
            raise HTTPException(
                status_code=400,
                detail="Question index cannot be negative.",
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

    # ===========================================================
    # CREATE EXAM
    # ===========================================================

    async def create_exam(
        self,
        db: AsyncSession,
        school_id: UUID,
        user: User,
        payload: CBTExamCreate,
    ) -> ExamApiResponse:
        session = await self.da.get_active_session(
            db,
            school_id=user.school_id,
        )

        term = await self.da.get_active_term(
            db,
            school_id=user.school_id,
        )

        if not session or not term:
            raise HTTPException(
                status_code=400,
                detail=("An active academic session and term are required."),
            )

        await self._validate_assessment_allocation(
            db,
            school_id=school_id,
            session_id=session.id,
            term_id=term.id,
            payload=payload,
        )

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
            assessment_type=payload.assessment_type,
            assessment_number=payload.assessment_number,
            assessment_label=self._assessment_label(
                payload.assessment_type,
                payload.assessment_number,
            ),
            contribution_marks=payload.contribution_marks,
            max_attempts=payload.max_attempts,
            # Newly created assessments participate in academic results.
            is_result_assessment=True,
        )

        exam = await self.repo.create_exam(
            db,
            exam,
        )

        exam = await self.repo.get_exam(
            db,
            exam.id,
        )

        return ExamApiResponse(
            success=True,
            message="Exam created successfully.",
            data=ExamResponse.model_validate(exam),
        )

    # ===========================================================
    # UPDATE EXAM
    # ===========================================================

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
            raise HTTPException(
                status_code=404,
                detail="Examination not found.",
            )

        if exam.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot modify this examination.",
            )

        if exam.is_published:
            raise HTTPException(
                status_code=400,
                detail="Published examinations cannot be edited.",
            )

        await self._validate_assessment_allocation(
            db,
            school_id=school_id,
            session_id=exam.session_id,
            term_id=exam.term_id,
            payload=payload,
            exclude_exam_id=exam.id,
        )

        exam.class_id = payload.class_id
        exam.subject_id = payload.subject_id

        exam.assessment_type = payload.assessment_type
        exam.assessment_number = payload.assessment_number
        exam.assessment_label = self._assessment_label(
            payload.assessment_type,
            payload.assessment_number,
        )
        exam.contribution_marks = payload.contribution_marks

        exam.max_attempts = payload.max_attempts

        exam.title = payload.title
        exam.instructions = payload.instructions
        exam.duration_minutes = payload.duration_minutes
        exam.total_marks = payload.total_marks

        # Updating through the official assessment form promotes
        # a legacy exam into an official result assessment.
        exam.is_result_assessment = True

        await db.commit()
        await db.refresh(exam)

        return {
            "success": True,
            "message": "Examination updated successfully.",
            "data": ExamResponse.model_validate(exam),
        }

    # ===========================================================
    # QUESTIONS
    # ===========================================================

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

        question = await self.repo.create_question(
            db,
            question,
        )

        for index, option in enumerate(payload.options):
            option_model = CBTQuestionOption(
                question_id=question.id,
                option_label=chr(65 + index),
                option_text=option.option_text,
                option_order=index + 1,
                is_correct=option.is_correct,
            )

            await self.repo.create_option(
                db,
                option_model,
            )

        question = await self.repo.get_question(
            db,
            question.id,
        )

        return QuestionApiResponse(
            success=True,
            message="Question added successfully.",
            data=QuestionResponse.model_validate(question),
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

        question.question = payload.question_text
        question.marks = payload.marks
        question.question_order = payload.order_no

        await self.repo.delete_question_options(
            db,
            question.id,
        )

        for index, option in enumerate(payload.options):
            new_option = CBTQuestionOption(
                question_id=question.id,
                option_label=chr(65 + index),
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

    # ===========================================================
    # PUBLISH / DELETE EXAM
    # ===========================================================

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

    # ===========================================================
    # STUDENT AVAILABLE EXAMS
    # ===========================================================

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
                    # Assessment information
                    assessment_type=exam.assessment_type,
                    assessment_label=exam.assessment_label,
                    contribution_marks=exam.contribution_marks,
                    # Attempt configuration
                    max_attempts=exam.max_attempts,
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

    # ===========================================================
    # START EXAM
    # ===========================================================

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

        existing = await self.repo.get_active_student_attempt(
            db,
            exam_id,
            student_id,
        )

        attempt_count = await self.repo.count_student_attempts(
            db,
            exam_id,
            student_id,
        )

        # Resume an existing unfinished attempt.
        if existing:
            elapsed_seconds = int((now - existing.started_at).total_seconds())

            allowed_seconds = exam.duration_minutes * 60

            if elapsed_seconds >= allowed_seconds:
                await self.submit_exam(
                    db=db,
                    attempt_id=existing.id,
                    student_id=student_id,
                )

                return StudentExamAttemptApiResponse(
                    success=False,
                    message=(
                        "Your examination time has elapsed "
                        "and your exam has been submitted."
                    ),
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

        if attempt_count >= exam.max_attempts:
            return StudentExamAttemptApiResponse(
                success=False,
                message=("You have used all permitted attempts for this assessment."),
                data=None,
            )

        attempt = CBTAttempt(
            school_id=exam.school_id,
            exam_id=exam.id,
            student_id=student_id,
            attempt_number=attempt_count + 1,
            started_at=now,
            score=0,
            contribution_score=0,
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

    # ===========================================================
    # SUBMIT ANSWER
    # ===========================================================

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

        if attempt.student_id != student_id:
            return AnswerApiResponse(
                success=False,
                message="Unauthorized attempt.",
                data=None,
            )

        if attempt.submitted_at is not None:
            return AnswerApiResponse(
                success=False,
                message="Exam already submitted.",
                data=None,
            )

        exam = attempt.exam
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
                message=("Time has elapsed. Your examination has been submitted."),
                data=None,
            )

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

    # ===========================================================
    # SCHOOL EXAMS
    # ===========================================================

    async def get_school_exams(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> ExamListApiResponse:
        # Includes official and legacy CBT examinations.
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

    # ===========================================================
    # EXAM RESULTS / ATTEMPTS
    # ===========================================================

    async def get_exam_results(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ) -> AttemptListApiResponse:
        # Legacy exam attempts remain visible here.
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
        scores = [attempt.score for attempt in attempts]

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
                attempts=[
                    AttemptResponse.model_validate(attempt) for attempt in attempts
                ],
                count=len(attempts),
                average_score=round(
                    sum(scores) / len(scores),
                    2,
                ),
                highest_score=max(scores),
                lowest_score=min(scores),
                passed_count=sum(1 for attempt in attempts if attempt.is_passed),
                failed_count=sum(1 for attempt in attempts if not attempt.is_passed),
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

    # ===========================================================
    # RESUME EXAM
    # ===========================================================

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

        attempt = await self.repo.get_student_attempt_details(
            db,
            attempt.id,
        )

        return StudentExamAttemptApiResponse(
            success=True,
            message="Exam resumed successfully.",
            data=self.build_student_exam_response(attempt),
        )

    # ===========================================================
    # STUDENT RESULT
    # ===========================================================

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
                contribution_score=float(attempt.contribution_score or 0),
                attempt_number=attempt.attempt_number,
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

    # ===========================================================
    # STUDENT HISTORY
    # ===========================================================

    async def get_student_history(
        self,
        db: AsyncSession,
        student_id: UUID,
    ):
        # History includes both official and legacy CBT attempts.
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
                    contribution_score=float(attempt.contribution_score or 0),
                    attempt_number=attempt.attempt_number,
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

    # ===========================================================
    # RESULTS DASHBOARD
    # ===========================================================

    async def get_results_dashboard(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> CBTResultsDashboardApiResponse:
        """
        Returns the official CBT results dashboard.

        Legacy/practice exams are excluded by the repository.
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
                highest_score=round(
                    float(row["highest_score"]),
                    2,
                ),
                lowest_score=round(
                    float(row["lowest_score"]),
                    2,
                ),
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

    # ===========================================================
    # AUTOMATIC TERM RESULT SYNCHRONIZATION
    # ===========================================================

    async def _sync_attempt_to_term_result(
        self,
        db: AsyncSession,
        attempt: CBTAttempt,
    ) -> bool:
        """
        Synchronizes an official CBT attempt into the existing
        ResultBatch and ResultRecord.

        Official assessment allocation:

            CA1 = 20
            CA2 = 20
            Main Examination = 60

        Rules:

        - Legacy CBT exams never contribute to academic results.
        - Only official assessments are considered.
        - Best submitted attempt per assessment is used.
        - Published result batches are never modified.
        - Existing teacher comments are preserved.
        """

        # -------------------------------------------------------
        # 1. Retrieve the examination
        # -------------------------------------------------------

        exam_result = await db.execute(
            select(CBTExam).where(
                CBTExam.id == attempt.exam_id,
            )
        )

        exam = exam_result.scalar_one_or_none()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail=(
                    "The CBT examination associated with this attempt was not found."
                ),
            )

        # -------------------------------------------------------
        # 2. Ignore legacy/practice examinations
        # -------------------------------------------------------

        if not exam.is_result_assessment:
            return False

        # -------------------------------------------------------
        # 3. Get official assessments for this subject and term
        # -------------------------------------------------------

        assessments_result = await db.execute(
            select(CBTExam).where(
                CBTExam.school_id == exam.school_id,
                CBTExam.session_id == exam.session_id,
                CBTExam.term_id == exam.term_id,
                CBTExam.class_id == exam.class_id,
                CBTExam.subject_id == exam.subject_id,
                # Critical: legacy exams must not contribute.
                CBTExam.is_result_assessment.is_(True),
            )
        )

        assessments = list(assessments_result.scalars().all())

        if not assessments:
            return False

        assessment_ids = [assessment.id for assessment in assessments]

        # -------------------------------------------------------
        # 4. Get all submitted attempts for this student
        # -------------------------------------------------------

        attempts_result = await db.execute(
            select(CBTAttempt).where(
                CBTAttempt.exam_id.in_(assessment_ids),
                CBTAttempt.student_id == attempt.student_id,
                CBTAttempt.submitted_at.is_not(None),
                CBTAttempt.status.in_(
                    [
                        AttemptStatus.SUBMITTED,
                        AttemptStatus.AUTO_SUBMITTED,
                    ]
                ),
            )
        )

        submitted_attempts = list(attempts_result.scalars().all())

        # -------------------------------------------------------
        # 5. Keep the best attempt for each assessment
        # -------------------------------------------------------

        best_by_exam: dict[UUID, float] = {}

        for submitted in submitted_attempts:
            contribution = float(submitted.contribution_score or 0)

            current_best = best_by_exam.get(
                submitted.exam_id,
                0.0,
            )

            best_by_exam[submitted.exam_id] = max(
                current_best,
                contribution,
            )

        # -------------------------------------------------------
        # 6. Calculate CA1, CA2 and Main Examination separately
        # -------------------------------------------------------

        ca1_score = 0.0
        ca2_score = 0.0
        main_exam_score = 0.0

        for assessment in assessments:
            contribution = best_by_exam.get(
                assessment.id,
                0.0,
            )

            if assessment.assessment_type == AssessmentType.CA:
                if assessment.assessment_number == 1:
                    ca1_score += contribution

                elif assessment.assessment_number == 2:
                    ca2_score += contribution

            elif assessment.assessment_type == AssessmentType.EXAM:
                main_exam_score += contribution

        ca1_score = min(20.0, ca1_score)
        ca2_score = min(20.0, ca2_score)
        main_exam_score = min(60.0, main_exam_score)

        ca_score = round(
            min(40.0, ca1_score + ca2_score),
            2,
        )

        exam_score = round(
            min(60.0, main_exam_score),
            2,
        )

        total_score = round(
            min(100.0, ca_score + exam_score),
            2,
        )

        # -------------------------------------------------------
        # 7. Get or create the existing result batch
        # -------------------------------------------------------

        batch_result = await db.execute(
            select(ResultBatch).where(
                ResultBatch.school_id == exam.school_id,
                ResultBatch.class_id == exam.class_id,
                ResultBatch.session_id == exam.session_id,
                ResultBatch.term_id == exam.term_id,
            )
        )

        batch = batch_result.scalar_one_or_none()

        # Never overwrite published academic results.
        if batch is not None and batch.status == "PUBLISHED":
            return False

        if batch is None:
            batch = ResultBatch(
                school_id=exam.school_id,
                class_id=exam.class_id,
                session_id=exam.session_id,
                term_id=exam.term_id,
                created_by=None,
                status="DRAFT",
                requires_review=False,
            )

            db.add(batch)
            await db.flush()

        elif batch.status in ("SUBMITTED", "APPROVED"):
            # A changed CBT contribution requires another review.
            batch.requires_review = True

            if batch.status == "APPROVED":
                batch.status = "SUBMITTED"

        # -------------------------------------------------------
        # 8. Get the existing student subject result
        # -------------------------------------------------------

        record_result = await db.execute(
            select(ResultRecord).where(
                ResultRecord.batch_id == batch.id,
                ResultRecord.student_id == attempt.student_id,
                ResultRecord.subject_id == exam.subject_id,
            )
        )

        record = record_result.scalar_one_or_none()

        # -------------------------------------------------------
        # 9. Calculate grade and remark
        # -------------------------------------------------------

        result_service = ResultService()

        grade, remark = result_service.calculate_grade(total_score)

        # -------------------------------------------------------
        # 10. Create or update the existing result record
        # -------------------------------------------------------

        if record is None:
            record = ResultRecord(
                school_id=exam.school_id,
                batch_id=batch.id,
                student_id=attempt.student_id,
                subject_id=exam.subject_id,
                ca_score=ca_score,
                exam_score=exam_score,
                total_score=total_score,
                grade=grade,
                remark=remark,
                teacher_comment=None,
            )

            db.add(record)

        else:
            record.ca_score = ca_score
            record.exam_score = exam_score
            record.total_score = total_score
            record.grade = grade
            record.remark = remark

            # Preserve the existing teacher comment.

        # -------------------------------------------------------
        # 11. Recalculate batch totals
        # -------------------------------------------------------

        await db.flush()

        await result_service._recalculate_batch(
            db=db,
            batch_id=batch.id,
            school_id=exam.school_id,
        )

        return True

    # ===========================================================
    # SUBMIT EXAM
    # ===========================================================

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

        # -------------------------------------------------------
        # Idempotency
        # -------------------------------------------------------

        if attempt.submitted_at is not None:
            return StudentExamResultApiResponse(
                success=False,
                message="Exam has already been submitted.",
                data=None,
            )

        exam = attempt.exam

        # -------------------------------------------------------
        # Server timer
        # -------------------------------------------------------

        now = datetime.now(UTC)

        expires_at = attempt.started_at + timedelta(
            minutes=exam.duration_minutes,
        )

        completed_at = min(
            now,
            expires_at,
        )

        duration_taken = int((completed_at - attempt.started_at).total_seconds())

        # -------------------------------------------------------
        # Load answers
        # -------------------------------------------------------

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

        # -------------------------------------------------------
        # Calculate raw score and percentage
        # -------------------------------------------------------

        total_marks = exam.total_marks

        percentage = (
            round(
                (score / total_marks) * 100,
                2,
            )
            if total_marks > 0
            else 0
        )

        pass_mark = getattr(
            exam,
            "pass_mark",
            50,
        )

        is_passed = percentage >= pass_mark

        # -------------------------------------------------------
        # Calculate contribution score
        # -------------------------------------------------------

        # Legacy/practice exams must always have zero contribution.
        contribution_score = 0.0

        if exam.is_result_assessment:
            contribution_score = self.calculate_contribution(
                score=score,
                raw_total_marks=total_marks,
                contribution_marks=exam.contribution_marks,
            )

        # -------------------------------------------------------
        # Update attempt
        # -------------------------------------------------------

        attempt.score = score
        attempt.contribution_score = contribution_score
        attempt.percentage = percentage
        attempt.is_passed = is_passed

        attempt.status = (
            AttemptStatus.AUTO_SUBMITTED
            if now >= expires_at
            else AttemptStatus.SUBMITTED
        )

        attempt.submitted_at = completed_at
        attempt.duration_taken = duration_taken

        await self.repo.submit_attempt(
            db,
            attempt,
        )

        # -------------------------------------------------------
        # Automatically synchronize official term results
        # -------------------------------------------------------

        await self._sync_attempt_to_term_result(
            db,
            attempt,
        )

        # Commit the attempt even when synchronization is skipped
        # because this is a legacy/practice examination.
        await db.commit()

        # -------------------------------------------------------
        # Response
        # -------------------------------------------------------

        return StudentExamResultApiResponse(
            success=True,
            message="Exam submitted successfully.",
            data=StudentExamResultResponse(
                attempt_id=attempt.id,
                exam_id=exam.id,
                title=exam.title,
                score=score,
                total_marks=total_marks,
                contribution_score=float(attempt.contribution_score or 0),
                attempt_number=attempt.attempt_number,
                percentage=percentage,
                passed=is_passed,
                answered_questions=correct + wrong,
                correct_answers=correct,
                wrong_answers=wrong,
                unanswered_questions=unanswered,
                total_questions=len(exam.questions),
                completed_at=completed_at,
            ),
        )
