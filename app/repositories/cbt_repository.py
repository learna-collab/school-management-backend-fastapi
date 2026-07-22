from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cbt_answer import CBTAnswer
from app.models.cbt_attempt import CBTAttempt
from app.models.cbt_exam import CBTExam
from app.models.cbt_question import CBTQuestion
from app.models.cbt_question_option import CBTQuestionOption


class CBTRepository:
    async def create_exam(
        self,
        db: AsyncSession,
        exam: CBTExam,
    ):
        db.add(exam)

        await db.commit()
        await db.refresh(exam)

        return exam

    async def get_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        result = await db.execute(
            select(CBTExam)
            .where(CBTExam.id == exam_id)
            .options(
                selectinload(CBTExam.questions).selectinload(CBTQuestion.options),
                selectinload(CBTExam.school_class),
                selectinload(CBTExam.subject),
                selectinload(CBTExam.session),
                selectinload(CBTExam.term),
            )
        )

        return result.scalar_one_or_none()

    async def get_class_exams(
        self,
        db: AsyncSession,
        class_id: UUID,
    ):
        result = await db.execute(
            select(CBTExam).where(
                CBTExam.class_id == class_id,
                CBTExam.is_published == True,
            )
        )

        return result.scalars().all()

    async def create_question(
        self,
        db: AsyncSession,
        question: CBTQuestion,
    ):
        db.add(question)

        await db.commit()
        await db.refresh(question)

        return question

    async def create_option(
        self,
        db: AsyncSession,
        option: CBTQuestionOption,
    ):
        db.add(option)

        await db.commit()
        await db.refresh(option)

        return option

    async def publish_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        exam = await db.get(
            CBTExam,
            exam_id,
        )

        if not exam:
            return None

        exam.is_published = True

        await db.commit()
        await db.refresh(exam)

        return exam

    async def create_attempt(
        self,
        db: AsyncSession,
        attempt: CBTAttempt,
    ):
        db.add(attempt)

        await db.commit()
        await db.refresh(attempt)

        return attempt

    async def get_student_attempt(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ):
        result = await db.execute(
            select(CBTAttempt).where(
                CBTAttempt.exam_id == exam_id,
                CBTAttempt.student_id == student_id,
            )
        )

        return result.scalar_one_or_none()

    async def save_answer(
        self,
        db: AsyncSession,
        answer: CBTAnswer,
    ):
        db.add(answer)

        await db.commit()
        await db.refresh(answer)

        return answer

    async def update_answer(
        self,
        db: AsyncSession,
        answer: CBTAnswer,
    ):
        await db.commit()

        await db.refresh(answer)

        return answer

    async def get_attempt(
        self,
        db: AsyncSession,
        attempt_id: UUID,
    ):
        result = await db.execute(
            select(CBTAttempt)
            .where(CBTAttempt.id == attempt_id)
            .options(selectinload(CBTAttempt.answers))
        )

        return result.scalar_one_or_none()

    async def submit_attempt(
        self,
        db: AsyncSession,
        attempt: CBTAttempt,
    ):
        await db.commit()

        await db.refresh(attempt)

        return attempt

    async def delete_exam(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        exam = await db.get(
            CBTExam,
            exam_id,
        )

        if not exam:
            return False

        await db.delete(exam)

        await db.commit()

        return True

    async def get_answer(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        question_id: UUID,
    ):
        result = await db.execute(
            select(CBTAnswer).where(
                CBTAnswer.attempt_id == attempt_id,
                CBTAnswer.question_id == question_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_attempt_answers(
        self,
        db: AsyncSession,
        attempt_id: UUID,
    ):
        result = await db.execute(
            select(CBTAnswer)
            .where(CBTAnswer.attempt_id == attempt_id)
            .options(
                selectinload(CBTAnswer.question),
                selectinload(CBTAnswer.option),
            )
        )

        return result.scalars().all()

    async def create_answer(
        self,
        db: AsyncSession,
        answer: CBTAnswer,
    ):
        db.add(answer)

        await db.commit()

        await db.refresh(answer)

        return answer

    async def get_school_exams(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(CBTExam)
            .where(CBTExam.school_id == school_id)
            .options(
                # questions + options
                selectinload(CBTExam.questions).selectinload(CBTQuestion.options),
                # class details
                selectinload(CBTExam.school_class),
                # subject details
                selectinload(CBTExam.subject),
                # optional but useful
                selectinload(CBTExam.session),
                selectinload(CBTExam.term),
            )
            .order_by(CBTExam.created_at.desc())
        )

        return result.scalars().unique().all()

    async def get_question(
        self,
        db: AsyncSession,
        question_id: UUID,
    ):
        result = await db.execute(
            select(CBTQuestion)
            .where(CBTQuestion.id == question_id)
            .options(selectinload(CBTQuestion.options))
        )

        return result.scalar_one_or_none()

    async def delete_question_options(
        self,
        db: AsyncSession,
        question_id: UUID,
    ):
        await db.execute(
            delete(CBTQuestionOption).where(
                CBTQuestionOption.question_id == question_id
            )
        )

    async def delete_question(
        self,
        db: AsyncSession,
        question: CBTQuestion,
    ):
        await db.delete(question)

        await db.commit()

    async def get_exam_attempts(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        result = await db.execute(
            select(CBTAttempt)
            .where(CBTAttempt.exam_id == exam_id)
            .options(
                selectinload(CBTAttempt.student),
                selectinload(CBTAttempt.answers),
            )
        )

        return result.scalars().all()

    # ------------------------------------------------------------------
    # Student
    # ------------------------------------------------------------------

    async def get_student_attempt_history(
        self,
        db: AsyncSession,
        student_id: UUID,
    ):
        result = await db.execute(
            select(CBTAttempt)
            .where(CBTAttempt.student_id == student_id)
            .options(selectinload(CBTAttempt.exam))
            .order_by(CBTAttempt.started_at.desc())
        )

        return result.scalars().all()

    async def get_exam_by_id(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        result = await db.execute(
            select(CBTExam)
            .where(CBTExam.id == exam_id)
            .options(
                # questions + options
                selectinload(CBTExam.questions).selectinload(CBTQuestion.options),
                # class details
                selectinload(CBTExam.school_class),
                # subject details
                selectinload(CBTExam.subject),
                # optional but useful
                selectinload(CBTExam.session),
                selectinload(CBTExam.term),
            )
        )

        return result.scalar_one_or_none()
