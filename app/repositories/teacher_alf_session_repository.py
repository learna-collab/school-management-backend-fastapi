from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_teacher import ClassTeacher
from app.models.classes import Class
from app.models.enums.alf import ALFSessionStatus
from app.models.lesson import Lesson
from app.models.teacher_alf_session import TeacherALFSession


class TeacherALFSessionRepository:
    # ============================================================
    # SHARED EAGER-LOAD OPTIONS
    # ============================================================

    @staticmethod
    def _session_load_options():
        """
        All relationships required when converting a TeacherALFSession
        into an API response must be loaded explicitly.

        This is especially important with AsyncSession because lazy
        relationship loading can cause MissingGreenlet errors.
        """
        return (
            selectinload(TeacherALFSession.teacher),
            selectinload(TeacherALFSession.school_class),
            selectinload(TeacherALFSession.lesson).selectinload(
                Lesson.subject_template
            ),
            selectinload(TeacherALFSession.lesson).selectinload(Lesson.class_template),
            selectinload(TeacherALFSession.lesson).selectinload(Lesson.alf),
        )

    # ============================================================
    # CLASS / AUTHORIZATION
    # ============================================================

    async def get_teacher_class(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID,
        school_id: UUID,
    ) -> Class | None:
        result = await db.execute(
            select(Class)
            .join(
                ClassTeacher,
                ClassTeacher.class_id == Class.id,
            )
            .where(
                Class.id == class_id,
                Class.school_id == school_id,
                ClassTeacher.teacher_id == teacher_id,
                ClassTeacher.class_id == class_id,
                ClassTeacher.school_id == school_id,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # LESSON
    # ============================================================

    async def get_alf_lesson(
        self,
        db: AsyncSession,
        *,
        lesson_id: UUID,
    ) -> Lesson | None:
        """
        Load a lesson together with all relationships required
        during ALF session validation.
        """
        result = await db.execute(
            select(Lesson)
            .options(
                selectinload(Lesson.alf),
                selectinload(Lesson.subject_template),
                selectinload(Lesson.class_template),
            )
            .where(
                Lesson.id == lesson_id,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # ACTIVE SESSION
    # ============================================================

    async def get_active_session(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        lesson_id: UUID,
        class_id: UUID,
    ) -> TeacherALFSession | None:
        """
        Return the latest active session for this
        teacher + lesson + class combination.

        Every relationship required by to_response() is
        eagerly loaded.
        """
        result = await db.execute(
            select(TeacherALFSession)
            .options(*self._session_load_options())
            .where(
                TeacherALFSession.teacher_id == teacher_id,
                TeacherALFSession.lesson_id == lesson_id,
                TeacherALFSession.class_id == class_id,
                TeacherALFSession.status.in_(
                    [
                        ALFSessionStatus.STARTED,
                        ALFSessionStatus.IN_PROGRESS,
                    ]
                ),
            )
            .order_by(
                TeacherALFSession.started_at.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    # ============================================================
    # CREATE
    # ============================================================

    async def create(
        self,
        db: AsyncSession,
        session: TeacherALFSession,
    ) -> TeacherALFSession:
        """
        Persist a new session.

        The caller should re-fetch the session using get_by_id()
        after commit before converting it to a response.
        """
        db.add(session)
        await db.flush()

        return session

    # ============================================================
    # GET BY ID
    # ============================================================

    async def get_by_id(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> TeacherALFSession | None:
        """
        Retrieve a session with every relationship required by
        the service response layer.

        This method is intentionally the canonical way to retrieve
        a session for API responses.
        """
        result = await db.execute(
            select(TeacherALFSession)
            .options(*self._session_load_options())
            .where(
                TeacherALFSession.id == session_id,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # UPDATE PROGRESS
    # ============================================================

    async def update_progress(
        self,
        db: AsyncSession,
        *,
        session: TeacherALFSession,
        independent_reading_completed: bool | None = None,
        mini_lesson_completed: bool | None = None,
        case_study_completed: bool | None = None,
        project_based_learning_completed: bool | None = None,
        evaluation_completed: bool | None = None,
        last_activity_at: datetime,
        status: ALFSessionStatus | None = None,
    ) -> TeacherALFSession:
        if independent_reading_completed is not None:
            session.independent_reading_completed = independent_reading_completed

        if mini_lesson_completed is not None:
            session.mini_lesson_completed = mini_lesson_completed

        if case_study_completed is not None:
            session.case_study_completed = case_study_completed

        if project_based_learning_completed is not None:
            session.project_based_learning_completed = project_based_learning_completed

        if evaluation_completed is not None:
            session.evaluation_completed = evaluation_completed

        session.last_activity_at = last_activity_at

        if status is not None:
            session.status = status

        await db.flush()

        return session

    # ============================================================
    # COMPLETE
    # ============================================================

    async def complete(
        self,
        db: AsyncSession,
        *,
        session: TeacherALFSession,
        completed_at: datetime,
        duration_seconds: int,
    ) -> TeacherALFSession:
        session.status = ALFSessionStatus.COMPLETED
        session.completed_at = completed_at
        session.last_activity_at = completed_at
        session.duration_seconds = duration_seconds

        await db.flush()

        return session

    # ============================================================
    # TEACHER HISTORY
    # ============================================================

    async def get_teacher_sessions(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        class_id: UUID | None = None,
        lesson_id: UUID | None = None,
        status: ALFSessionStatus | None = None,
    ) -> list[TeacherALFSession]:
        query = (
            select(TeacherALFSession)
            .options(*self._session_load_options())
            .where(
                TeacherALFSession.teacher_id == teacher_id,
            )
            .order_by(
                TeacherALFSession.started_at.desc(),
            )
        )

        if class_id is not None:
            query = query.where(
                TeacherALFSession.class_id == class_id,
            )

        if lesson_id is not None:
            query = query.where(
                TeacherALFSession.lesson_id == lesson_id,
            )

        if status is not None:
            query = query.where(
                TeacherALFSession.status == status,
            )

        result = await db.execute(query)

        return list(result.scalars().all())
