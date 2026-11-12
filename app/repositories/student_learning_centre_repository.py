from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.orm import selectinload

from app.models.enrollment import StudentEnrollment
from app.models.lesson import Lesson
from app.models.lesson_learning_content import LessonLearningContent
from app.models.student_learning_progress import StudentLearningProgress
from app.repositories.dashboard_repository import DashboardRepository


class StudentLearningCentreRepository:
    def __init__(self):
        self.dashboard_repo = DashboardRepository()

    # ==========================================================
    # STUDENT CONTEXT
    # ==========================================================

    async def get_student_context(self, db, user):
        """
        Resolve the student's current enrollment and active
        academic period using the authenticated user.
        """

        if not user.school_id:
            return None

        period = await self.dashboard_repo.get_current_period(
            db=db,
            school_id=user.school_id,
        )

        if not period or not period.session or not period.term:
            return None

        result = await db.execute(
            select(StudentEnrollment)
            .options(
                selectinload(StudentEnrollment.school_class),
                selectinload(StudentEnrollment.session),
            )
            .where(
                StudentEnrollment.student_id == user.id,
                StudentEnrollment.school_id == user.school_id,
                StudentEnrollment.is_current.is_(True),
                StudentEnrollment.session_id == period.session.id,
            )
        )

        enrollment = result.scalar_one_or_none()

        if not enrollment:
            return None

        school_class = enrollment.school_class

        if not school_class:
            return None

        # Custom classes do not have a shared lesson-template mapping.
        template_class_id = school_class.template_class_id

        if school_class.is_custom or not template_class_id:
            return {
                "school_id": user.school_id,
                "class_id": school_class.id,
                "class_name": school_class.name,
                "class_template_id": None,
                "session_id": period.session.id,
                "term_id": period.term.id,
                "custom_class": True,
            }

        return {
            "school_id": user.school_id,
            "class_id": school_class.id,
            "class_name": school_class.name,
            "class_template_id": template_class_id,
            "session_id": period.session.id,
            "term_id": period.term.id,
            "custom_class": False,
        }

    # ==========================================================
    # PUBLISHED LESSON CONTENT
    # ==========================================================

    async def get_published_contents(
        self,
        db,
        *,
        class_template_id: UUID,
        session_id: UUID,
        term_id: UUID,
        school_id: UUID,
        week_number: int | None = None,
    ):
        stmt = (
            select(LessonLearningContent)
            .join(
                Lesson,
                Lesson.id == LessonLearningContent.lesson_id,
            )
            .options(
                selectinload(LessonLearningContent.lesson),
            )
            .where(
                Lesson.class_template_id == class_template_id,
                Lesson.session_id == session_id,
                Lesson.term_id == term_id,
                Lesson.is_published.is_(True),
                LessonLearningContent.status == "PUBLISHED",
                (
                    (LessonLearningContent.school_id == school_id)
                    | (LessonLearningContent.school_id.is_(None))
                ),
            )
            .order_by(
                Lesson.week_number,
                case(
                    (
                        LessonLearningContent.school_id == school_id,
                        1,
                    ),
                    else_=0,
                ).desc(),
                LessonLearningContent.version.desc(),
            )
        )

        if week_number is not None:
            stmt = stmt.where(Lesson.week_number == week_number)

        result = await db.execute(stmt)

        # A lesson can have several published versions.
        # Return only the newest applicable version.
        selected = {}
        for content in result.scalars().all():
            if content.lesson_id not in selected:
                selected[content.lesson_id] = content

        return list(selected.values())

    async def get_published_content(
        self,
        db,
        *,
        content_id: UUID,
        class_template_id: UUID,
        session_id: UUID,
        term_id: UUID,
        school_id: UUID,
    ):
        stmt = (
            select(LessonLearningContent)
            .join(
                Lesson,
                Lesson.id == LessonLearningContent.lesson_id,
            )
            .options(
                selectinload(LessonLearningContent.lesson),
            )
            .where(
                LessonLearningContent.id == content_id,
                LessonLearningContent.status == "PUBLISHED",
                LessonLearningContent.lesson_id == Lesson.id,
                Lesson.class_template_id == class_template_id,
                Lesson.session_id == session_id,
                Lesson.term_id == term_id,
                Lesson.is_published.is_(True),
                (
                    (LessonLearningContent.school_id == school_id)
                    | (LessonLearningContent.school_id.is_(None))
                ),
            )
            .order_by(
                case(
                    (
                        LessonLearningContent.school_id == school_id,
                        1,
                    ),
                    else_=0,
                ).desc(),
                LessonLearningContent.version.desc(),
            )
            .limit(1)
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    # ==========================================================
    # STUDENT PROGRESS
    # ==========================================================

    async def get_progress(
        self,
        db,
        *,
        content_id: UUID,
        student_id: UUID,
        school_id: UUID,
    ):
        result = await db.execute(
            select(StudentLearningProgress).where(
                StudentLearningProgress.learning_content_id == content_id,
                StudentLearningProgress.student_id == student_id,
                StudentLearningProgress.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_or_create_progress(
        self,
        db,
        *,
        content_id: UUID,
        student_id: UUID,
        school_id: UUID,
    ):
        progress = await self.get_progress(
            db,
            content_id=content_id,
            student_id=student_id,
            school_id=school_id,
        )

        if progress:
            return progress

        progress = StudentLearningProgress(
            learning_content_id=content_id,
            student_id=student_id,
            school_id=school_id,
            status="NOT_STARTED",
            attempts_count=0,
            score=None,
            activity_progress={},
        )

        db.add(progress)

        try:
            await db.flush()
        except Exception:
            await db.rollback()

            # Another request may have created the row
            # concurrently. Fetch that row instead.
            progress = await self.get_progress(
                db,
                content_id=content_id,
                student_id=student_id,
                school_id=school_id,
            )

            if not progress:
                raise

        return progress

    async def get_progress_for_update(
        self,
        db,
        *,
        content_id: UUID,
        student_id: UUID,
        school_id: UUID,
    ):
        result = await db.execute(
            select(StudentLearningProgress)
            .where(
                StudentLearningProgress.learning_content_id == content_id,
                StudentLearningProgress.student_id == student_id,
                StudentLearningProgress.school_id == school_id,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()


student_learning_centre_repo = StudentLearningCentreRepository()
