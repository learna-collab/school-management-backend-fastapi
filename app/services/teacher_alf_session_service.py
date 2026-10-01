from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums.alf import ALFSessionStatus
from app.models.teacher_alf_session import TeacherALFSession
from app.repositories.teacher_alf_session_repository import (
    TeacherALFSessionRepository,
)
from app.schemas.teacher_alf_session import ALFSessionResponse


class TeacherALFSessionService:
    """
    Handles teacher usage of ALF lessons.

    Responsibilities:
    - Verify teacher/class authorization
    - Verify lesson/class compatibility
    - Start ALF sessions
    - Track section progress
    - Complete sessions
    - Calculate duration server-side
    - Retrieve teacher session history
    """

    TOTAL_ALF_SECTIONS = 5

    def __init__(self):
        self.repository = TeacherALFSessionRepository()

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _calculate_progress(
        cls,
        session: TeacherALFSession,
    ) -> int:
        completed_sections = sum(
            [
                session.independent_reading_completed,
                session.mini_lesson_completed,
                session.case_study_completed,
                session.project_based_learning_completed,
                session.evaluation_completed,
            ]
        )

        return int(completed_sections / cls.TOTAL_ALF_SECTIONS * 100)

    @staticmethod
    def _is_complete(
        session: TeacherALFSession,
    ) -> bool:
        return (
            session.independent_reading_completed
            and session.mini_lesson_completed
            and session.case_study_completed
            and session.project_based_learning_completed
            and session.evaluation_completed
        )

    # ============================================================
    # START SESSION
    # ============================================================

    async def start_session(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        school_id: UUID,
        lesson_id: UUID,
        class_id: UUID,
    ) -> TeacherALFSession:
        """
        Start an ALF session for a teacher.

        teacher_id comes exclusively from authentication.
        It must never come from the frontend.
        """

        # --------------------------------------------------------
        # 1. Verify teacher is assigned to this class
        # --------------------------------------------------------

        school_class = await self.repository.get_teacher_class(
            db,
            teacher_id=teacher_id,
            class_id=class_id,
            school_id=school_id,
        )

        if not school_class:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this class.",
            )

        # --------------------------------------------------------
        # 2. Custom classes do not currently support generic ALF
        # --------------------------------------------------------

        if school_class.is_custom:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("ALF lessons are not available for custom classes."),
            )

        # --------------------------------------------------------
        # 3. Class must have an academic template
        # --------------------------------------------------------

        if not school_class.template_class_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("This class is not linked to an academic class template."),
            )

        # --------------------------------------------------------
        # 4. Load lesson + ALF
        # --------------------------------------------------------

        lesson = await self.repository.get_alf_lesson(
            db,
            lesson_id=lesson_id,
        )

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found.",
            )

        # --------------------------------------------------------
        # 5. Lesson must be published
        # --------------------------------------------------------

        if not lesson.is_published:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This lesson has not been published.",
            )

        # --------------------------------------------------------
        # 6. Lesson must have ALF content
        # --------------------------------------------------------

        if not lesson.alf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This lesson does not have ALF content.",
            )

        # --------------------------------------------------------
        # 7. Lesson must belong to the selected class template
        # --------------------------------------------------------

        if lesson.class_template_id != school_class.template_class_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=("This lesson is not available for the selected class."),
            )

        # --------------------------------------------------------
        # 8. Return existing active session if one exists
        # --------------------------------------------------------

        existing_session = await self.repository.get_active_session(
            db,
            teacher_id=teacher_id,
            lesson_id=lesson_id,
            class_id=class_id,
        )

        if existing_session:
            return existing_session

        # --------------------------------------------------------
        # 9. Create a new session
        # --------------------------------------------------------

        now = self._utc_now()

        session = TeacherALFSession(
            teacher_id=teacher_id,
            lesson_id=lesson_id,
            class_id=class_id,
            started_at=now,
            last_activity_at=now,
            completed_at=None,
            duration_seconds=0,
            status=ALFSessionStatus.STARTED,
            independent_reading_completed=False,
            mini_lesson_completed=False,
            case_study_completed=False,
            project_based_learning_completed=False,
            evaluation_completed=False,
        )

        await self.repository.create(
            db,
            session,
        )

        await db.commit()

        # --------------------------------------------------------
        # 10. IMPORTANT:
        # Re-fetch after commit with eager-loaded relationships.
        #
        # This prevents MissingGreenlet and also protects against
        # expire_on_commit invalidating relationship attributes.
        # --------------------------------------------------------

        fresh_session = await self.repository.get_by_id(
            db,
            session.id,
        )

        if not fresh_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve the newly created ALF session.",
            )

        return fresh_session

    # ============================================================
    # UPDATE PROGRESS
    # ============================================================

    async def update_progress(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        session_id: UUID,
        independent_reading_completed: bool | None = None,
        mini_lesson_completed: bool | None = None,
        case_study_completed: bool | None = None,
        project_based_learning_completed: bool | None = None,
        evaluation_completed: bool | None = None,
    ) -> TeacherALFSession:
        session = await self.repository.get_by_id(
            db,
            session_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ALF session not found.",
            )

        # --------------------------------------------------------
        # Verify ownership
        # --------------------------------------------------------

        if session.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this ALF session.",
            )

        # --------------------------------------------------------
        # Completed sessions cannot be modified
        # --------------------------------------------------------

        if session.status == ALFSessionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ALF session has already been completed.",
            )

        # --------------------------------------------------------
        # Abandoned sessions cannot be modified
        # --------------------------------------------------------

        if session.status == ALFSessionStatus.ABANDONED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ALF session has been abandoned.",
            )

        # --------------------------------------------------------
        # Update progress
        # --------------------------------------------------------

        now = self._utc_now()

        await self.repository.update_progress(
            db,
            session=session,
            independent_reading_completed=(independent_reading_completed),
            mini_lesson_completed=mini_lesson_completed,
            case_study_completed=case_study_completed,
            project_based_learning_completed=(project_based_learning_completed),
            evaluation_completed=evaluation_completed,
            last_activity_at=now,
            status=ALFSessionStatus.IN_PROGRESS,
        )

        await db.commit()

        # --------------------------------------------------------
        # Re-fetch with eager-loaded relationships
        # --------------------------------------------------------

        fresh_session = await self.repository.get_by_id(
            db,
            session.id,
        )

        if not fresh_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve the updated ALF session.",
            )

        return fresh_session

    # ============================================================
    # COMPLETE SESSION
    # ============================================================

    async def complete_session(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        session_id: UUID,
    ) -> TeacherALFSession:
        session = await self.repository.get_by_id(
            db,
            session_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ALF session not found.",
            )

        # --------------------------------------------------------
        # Verify ownership
        # --------------------------------------------------------

        if session.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this ALF session.",
            )

        # --------------------------------------------------------
        # Already completed
        # --------------------------------------------------------

        if session.status == ALFSessionStatus.COMPLETED:
            return session

        # --------------------------------------------------------
        # Abandoned sessions cannot be completed
        # --------------------------------------------------------

        if session.status == ALFSessionStatus.ABANDONED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ALF session has been abandoned.",
            )

        # --------------------------------------------------------
        # All five ALF sections must be completed
        # --------------------------------------------------------

        if not self._is_complete(session):
            progress = self._calculate_progress(session)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"ALF session is only {progress}% complete. "
                    "Complete all ALF sections before finishing "
                    "the session."
                ),
            )

        # --------------------------------------------------------
        # Calculate duration on the server
        # --------------------------------------------------------

        now = self._utc_now()

        duration_seconds = max(
            0,
            int((now - session.started_at).total_seconds()),
        )

        await self.repository.complete(
            db,
            session=session,
            completed_at=now,
            duration_seconds=duration_seconds,
        )

        await db.commit()

        # --------------------------------------------------------
        # Re-fetch with eager-loaded relationships
        # --------------------------------------------------------

        fresh_session = await self.repository.get_by_id(
            db,
            session.id,
        )

        if not fresh_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve the completed ALF session.",
            )

        return fresh_session

    # ============================================================
    # GET SINGLE SESSION
    # ============================================================

    async def get_session(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        session_id: UUID,
    ) -> TeacherALFSession:
        session = await self.repository.get_by_id(
            db,
            session_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ALF session not found.",
            )

        # --------------------------------------------------------
        # Verify ownership
        # --------------------------------------------------------

        if session.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this ALF session.",
            )

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
        return await self.repository.get_teacher_sessions(
            db,
            teacher_id=teacher_id,
            class_id=class_id,
            lesson_id=lesson_id,
            status=status,
        )

    # ============================================================
    # PROGRESS PERCENTAGE
    # ============================================================

    @classmethod
    def get_progress_percentage(
        cls,
        session: TeacherALFSession,
    ) -> int:
        return cls._calculate_progress(session)

    # ============================================================
    # RESPONSE MAPPING
    # ============================================================

    def to_response(
        self,
        session: TeacherALFSession,
    ) -> ALFSessionResponse:
        """
        Convert a fully hydrated TeacherALFSession into the API
        response.

        IMPORTANT:
        This method intentionally performs no database access.
        All required relationships must already be loaded by the
        repository.
        """

        teacher_name = " ".join(
            part
            for part in (
                session.teacher.first_name,
                session.teacher.last_name,
            )
            if part
        ).strip()

        subject_name = (
            session.lesson.subject_template.name
            if session.lesson.subject_template
            else "Unknown Subject"
        )

        return ALFSessionResponse(
            id=session.id,
            teacher_id=session.teacher_id,
            teacher_name=teacher_name,
            lesson_id=session.lesson_id,
            lesson_title=session.lesson.title,
            subject_name=subject_name,
            class_id=session.class_id,
            class_name=session.school_class.name,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            completed_at=session.completed_at,
            duration_seconds=session.duration_seconds,
            status=session.status,
            independent_reading_completed=(session.independent_reading_completed),
            mini_lesson_completed=session.mini_lesson_completed,
            case_study_completed=session.case_study_completed,
            project_based_learning_completed=(session.project_based_learning_completed),
            evaluation_completed=session.evaluation_completed,
            progress_percentage=self.get_progress_percentage(session),
        )
