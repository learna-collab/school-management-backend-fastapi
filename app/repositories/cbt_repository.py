from uuid import UUID

from sqlalchemy import Float, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.cbt_answer import CBTAnswer
from app.models.cbt_attempt import CBTAttempt
from app.models.cbt_exam import AssessmentType, CBTExam
from app.models.cbt_question import CBTQuestion
from app.models.cbt_question_option import CBTQuestionOption
from app.models.classes import Class
from app.models.subject import Subject


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

    async def get_student_available_exams(
        self,
        db: AsyncSession,
        class_id: UUID,
        student_id: UUID,
    ):
        """
        Retrieve published examinations for the student's current class.

        Includes both legacy and official examinations.

        Retrieves the student's latest attempt for each examination,
        if one exists.
        """

        # Use an alias so the nested query does not conflict with
        # the CBTAttempt table joined by the outer query.
        latestAttempt = aliased(CBTAttempt)

        latest_attempt_id = (
            select(latestAttempt.id)
            .where(
                latestAttempt.exam_id == CBTExam.id,
                latestAttempt.student_id == student_id,
            )
            .order_by(
                latestAttempt.attempt_number.desc(),
            )
            .limit(1)
            .correlate(CBTExam)
            .scalar_subquery()
        )

        stmt = (
            select(CBTExam, CBTAttempt)
            .outerjoin(
                CBTAttempt,
                CBTAttempt.id == latest_attempt_id,
            )
            .where(
                CBTExam.class_id == class_id,
                CBTExam.is_published.is_(True),
            )
            .options(
                selectinload(CBTExam.school_class),
                selectinload(CBTExam.subject),
                selectinload(CBTExam.questions),
            )
            .order_by(
                CBTExam.starts_at.asc(),
            )
        )

        result = await db.execute(stmt)

        return [
            {
                "exam": exam,
                "attempt": attempt,
            }
            for exam, attempt in result.all()
        ]

    async def get_exam_for_student(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        result = await db.execute(
            select(CBTExam)
            .where(CBTExam.id == exam_id)
            .options(
                selectinload(CBTExam.questions).selectinload(CBTQuestion.options),
                selectinload(CBTExam.subject),
                selectinload(CBTExam.school_class),
            )
        )

        return result.scalar_one_or_none()

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

    async def get_active_student_attempt(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ) -> CBTAttempt | None:
        stmt = (
            select(CBTAttempt)
            .where(
                CBTAttempt.exam_id == exam_id,
                CBTAttempt.student_id == student_id,
                CBTAttempt.submitted_at.is_(None),
            )
            .options(
                selectinload(CBTAttempt.exam)
                .selectinload(CBTExam.questions)
                .selectinload(CBTQuestion.options),
                selectinload(CBTAttempt.answers).selectinload(CBTAnswer.question),
                selectinload(CBTAttempt.answers).selectinload(
                    CBTAnswer.selected_option
                ),
            )
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    async def update_current_question(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        current_question_index: int,
    ):
        attempt = await db.get(
            CBTAttempt,
            attempt_id,
        )

        if not attempt:
            return None

        attempt.current_question_index = current_question_index

        await db.commit()
        await db.refresh(attempt)

        return attempt

    async def get_student_attempt_details(
        self,
        db: AsyncSession,
        attempt_id: UUID,
    ):
        result = await db.execute(
            select(CBTAttempt)
            .where(CBTAttempt.id == attempt_id)
            .options(
                selectinload(CBTAttempt.answers).selectinload(
                    CBTAnswer.selected_option
                ),
                selectinload(CBTAttempt.exam).selectinload(CBTExam.subject),
                selectinload(CBTAttempt.exam)
                .selectinload(CBTExam.questions)
                .selectinload(CBTQuestion.options),
            )
        )

        return result.scalar_one_or_none()

    async def get_student_exam_attempt(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ):
        result = await db.execute(
            select(CBTAttempt)
            .where(
                CBTAttempt.exam_id == exam_id,
                CBTAttempt.student_id == student_id,
            )
            .order_by(CBTAttempt.attempt_number.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def count_student_attempts(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ) -> int:
        result = await db.execute(
            select(func.count(CBTAttempt.id)).where(
                CBTAttempt.exam_id == exam_id,
                CBTAttempt.student_id == student_id,
            )
        )

        return int(result.scalar_one() or 0)

    async def get_latest_student_attempt(
        self,
        db: AsyncSession,
        exam_id: UUID,
        student_id: UUID,
    ) -> CBTAttempt | None:
        result = await db.execute(
            select(CBTAttempt)
            .where(
                CBTAttempt.exam_id == exam_id,
                CBTAttempt.student_id == student_id,
            )
            .order_by(CBTAttempt.attempt_number.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_assessment_allocation(
        self,
        db: AsyncSession,
        *,
        school_id: UUID,
        session_id: UUID,
        term_id: UUID,
        class_id: UUID,
        subject_id: UUID,
        assessment_type: str,
        exclude_exam_id: UUID | None = None,
    ) -> int:
        """
        Returns the total allocated marks for official assessments only.

        Legacy CBT exams are deliberately excluded because they do not
        contribute to academic results.
        """

        stmt = select(
            func.coalesce(
                func.sum(CBTExam.contribution_marks),
                0,
            )
        ).where(
            CBTExam.school_id == school_id,
            CBTExam.session_id == session_id,
            CBTExam.term_id == term_id,
            CBTExam.class_id == class_id,
            CBTExam.subject_id == subject_id,
            CBTExam.assessment_type == AssessmentType(assessment_type),
            CBTExam.is_result_assessment.is_(True),
        )

        if exclude_exam_id:
            stmt = stmt.where(
                CBTExam.id != exclude_exam_id,
            )

        result = await db.execute(stmt)

        return int(result.scalar_one() or 0)

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
            .options(
                selectinload(CBTAttempt.answers),
            )
        )

        return result.scalar_one_or_none()

    async def submit_attempt(
        self,
        db: AsyncSession,
        attempt: CBTAttempt,
    ):
        # The service performs the attempt save and term-result
        # synchronization in one transaction, then commits.
        await db.flush()

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
            .where(
                CBTAnswer.attempt_id == attempt_id,
            )
            .options(
                selectinload(CBTAnswer.question),
                selectinload(CBTAnswer.selected_option),
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
        # Return both official and legacy exams.
        result = await db.execute(
            select(CBTExam)
            .where(
                CBTExam.school_id == school_id,
            )
            .options(
                selectinload(CBTExam.questions).selectinload(CBTQuestion.options),
                selectinload(CBTExam.school_class),
                selectinload(CBTExam.subject),
                selectinload(CBTExam.session),
                selectinload(CBTExam.term),
            )
            .order_by(
                CBTExam.created_at.desc(),
            )
        )

        return result.scalars().unique().all()

    async def get_question(
        self,
        db: AsyncSession,
        question_id: UUID,
    ):
        result = await db.execute(
            select(CBTQuestion)
            .where(
                CBTQuestion.id == question_id,
            )
            .options(
                selectinload(CBTQuestion.options),
            )
        )

        return result.scalar_one_or_none()

    async def delete_question_options(
        self,
        db: AsyncSession,
        question_id: UUID,
    ):
        await db.execute(
            delete(CBTQuestionOption).where(
                CBTQuestionOption.question_id == question_id,
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
            .where(
                CBTAttempt.exam_id == exam_id,
            )
            .options(
                selectinload(CBTAttempt.student),
                selectinload(CBTAttempt.answers),
                selectinload(CBTAttempt.exam).selectinload(CBTExam.school_class),
                selectinload(CBTAttempt.exam).selectinload(CBTExam.subject),
                selectinload(CBTAttempt.exam).selectinload(CBTExam.questions),
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
        # Keep legacy attempts in the student's CBT history.
        result = await db.execute(
            select(CBTAttempt)
            .options(selectinload(CBTAttempt.exam).selectinload(CBTExam.subject))
            .where(
                CBTAttempt.student_id == student_id,
            )
            .order_by(
                CBTAttempt.started_at.desc(),
            )
        )

        return result.scalars().all()

    async def get_exam_by_id(
        self,
        db: AsyncSession,
        exam_id: UUID,
    ):
        result = await db.execute(
            select(CBTExam)
            .where(
                CBTExam.id == exam_id,
            )
            .options(
                selectinload(CBTExam.questions).selectinload(CBTQuestion.options),
                selectinload(CBTExam.school_class),
                selectinload(CBTExam.subject),
                selectinload(CBTExam.session),
                selectinload(CBTExam.term),
            )
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Official CBT Results Dashboard
    # ------------------------------------------------------------------

    async def get_results_dashboard(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        Returns one row per CBT exam created by the school.

        Includes both official result assessments and legacy/practice exams.
        Each exam's statistics are calculated from its associated attempts.
        """

        pass_count = func.sum(
            case(
                (
                    CBTAttempt.is_passed.is_(True),
                    1,
                ),
                else_=0,
            )
        )

        result = await db.execute(
            select(
                CBTExam.id.label("exam_id"),
                CBTExam.title,
                CBTExam.total_marks,
                CBTExam.starts_at,
                CBTExam.ends_at,
                CBTExam.is_published,
                Class.name.label("class_name"),
                Subject.name.label("subject_name"),
                func.count(
                    CBTAttempt.id,
                ).label("attempts"),
                func.coalesce(
                    func.avg(CBTAttempt.score),
                    0,
                ).label("average_score"),
                func.coalesce(
                    func.avg(CBTAttempt.percentage),
                    0,
                ).label("average_percentage"),
                func.coalesce(
                    func.max(CBTAttempt.score),
                    0,
                ).label("highest_score"),
                func.coalesce(
                    func.min(CBTAttempt.score),
                    0,
                ).label("lowest_score"),
                func.coalesce(
                    (
                        pass_count.cast(Float)
                        * 100
                        / func.nullif(
                            func.count(CBTAttempt.id),
                            0,
                        )
                    ),
                    0,
                ).label("pass_rate"),
            )
            .join(
                Class,
                CBTExam.class_id == Class.id,
            )
            .join(
                Subject,
                CBTExam.subject_id == Subject.id,
            )
            .outerjoin(
                CBTAttempt,
                CBTAttempt.exam_id == CBTExam.id,
            )
            .where(
                CBTExam.school_id == school_id,
                CBTExam.is_published.is_(True),
            )
            .group_by(
                CBTExam.id,
                CBTExam.title,
                CBTExam.total_marks,
                CBTExam.starts_at,
                CBTExam.ends_at,
                CBTExam.is_published,
                Class.name,
                Subject.name,
            )
            .order_by(
                CBTExam.starts_at.desc(),
            )
        )

        return result.mappings().all()

    async def get_results_dashboard_stats(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        Dashboard summary for all CBT exams created by the school,
        including official assessments and legacy/practice exams.
        """

        result = await db.execute(
            select(
                func.count(
                    func.distinct(CBTExam.id),
                ).label("total_exams"),
                func.count(
                    CBTAttempt.id,
                ).label("total_attempts"),
                func.coalesce(
                    func.avg(CBTAttempt.percentage),
                    0,
                ).label("average_percentage"),
                func.coalesce(
                    (
                        func.sum(
                            case(
                                (
                                    CBTAttempt.is_passed.is_(True),
                                    1,
                                ),
                                else_=0,
                            )
                        ).cast(Float)
                        * 100
                        / func.nullif(
                            func.count(CBTAttempt.id),
                            0,
                        )
                    ),
                    0,
                ).label("overall_pass_rate"),
            )
            .select_from(CBTExam)
            .outerjoin(
                CBTAttempt,
                CBTAttempt.exam_id == CBTExam.id,
            )
            .where(
                CBTExam.school_id == school_id,
                CBTExam.is_published.is_(True),
            )
        )

        return result.mappings().one()

    async def get_option(
        self,
        db: AsyncSession,
        option_id: UUID,
    ):
        result = await db.execute(
            select(CBTQuestionOption).where(
                CBTQuestionOption.id == option_id,
            )
        )

        return result.scalar_one_or_none()
