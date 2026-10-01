from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums.alf import ALFSessionStatus
from app.models.teacher_alf_session import TeacherALFSession
from app.repositories.teacher_alf_usage_repository import (
    TeacherALFUsageRepository,
)
from app.schemas.teacher_alf_usage import (
    ALFLessonUsageResponse,
    ALFTeacherUsageResponse,
    ALFUsageSessionResponse,
    ALFUsageStatsResponse,
)


class TeacherALFUsageService:
    def __init__(self):
        self.repository = TeacherALFUsageRepository()

    @staticmethod
    def _teacher_name(
        session: TeacherALFSession,
    ) -> str:
        return " ".join(
            part
            for part in (
                session.teacher.first_name,
                session.teacher.last_name,
            )
            if part
        ).strip()

    @staticmethod
    def _subject_name(
        session: TeacherALFSession,
    ) -> str:
        if session.lesson.subject_template:
            return session.lesson.subject_template.name

        return "Unknown Subject"

    @staticmethod
    def _progress(
        session: TeacherALFSession,
    ) -> int:
        completed = sum(
            [
                session.independent_reading_completed,
                session.mini_lesson_completed,
                session.case_study_completed,
                session.project_based_learning_completed,
                session.evaluation_completed,
            ]
        )

        return int((completed / 5) * 100)

    def to_response(
        self,
        session: TeacherALFSession,
    ) -> ALFUsageSessionResponse:
        return ALFUsageSessionResponse(
            id=session.id,
            teacher_id=session.teacher_id,
            teacher_name=self._teacher_name(session),
            lesson_id=session.lesson_id,
            lesson_title=session.lesson.title,
            subject_name=self._subject_name(session),
            class_id=session.class_id,
            class_name=session.school_class.name,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            completed_at=session.completed_at,
            duration_seconds=session.duration_seconds,
            status=session.status,
            independent_reading_completed=(session.independent_reading_completed),
            mini_lesson_completed=(session.mini_lesson_completed),
            case_study_completed=(session.case_study_completed),
            project_based_learning_completed=(session.project_based_learning_completed),
            evaluation_completed=(session.evaluation_completed),
            progress_percentage=self._progress(session),
        )

    async def get_sessions(
        self,
        db: AsyncSession,
        *,
        school_id: UUID | None = None,
        teacher_id: UUID | None = None,
        lesson_id: UUID | None = None,
        class_id: UUID | None = None,
        session_status: ALFSessionStatus | None = None,
    ) -> list[ALFUsageSessionResponse]:
        sessions = await self.repository.get_all_sessions(
            db,
            school_id=school_id,
            teacher_id=teacher_id,
            lesson_id=lesson_id,
            class_id=class_id,
            status=session_status,
        )

        return [self.to_response(session) for session in sessions]

    async def get_session(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        school_id: UUID | None = None,
    ) -> ALFUsageSessionResponse:
        session = await self.repository.get_session(
            db,
            session_id=session_id,
            school_id=school_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ALF session not found.",
            )

        return self.to_response(session)

    async def get_stats(
        self,
        db: AsyncSession,
        *,
        school_id: UUID | None = None,
    ) -> ALFUsageStatsResponse:
        stats = await self.repository.get_stats(
            db,
            school_id=school_id,
        )

        return ALFUsageStatsResponse(**stats)

    async def get_lesson_usage(
        self,
        db: AsyncSession,
        *,
        lesson_id: UUID,
        school_id: UUID | None = None,
    ) -> ALFLessonUsageResponse:
        sessions = await self.repository.get_all_sessions(
            db,
            school_id=school_id,
            lesson_id=lesson_id,
        )

        if not sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No ALF usage found for this lesson.",
            )

        first = sessions[0]

        total = len(sessions)

        completed = sum(
            session.status == ALFSessionStatus.COMPLETED for session in sessions
        )

        active = sum(
            session.status
            in {
                ALFSessionStatus.STARTED,
                ALFSessionStatus.IN_PROGRESS,
            }
            for session in sessions
        )

        total_duration = sum(session.duration_seconds for session in sessions)

        average_duration = int(total_duration / total) if total else 0

        completion_rate = completed / total * 100 if total else 0

        return ALFLessonUsageResponse(
            lesson_id=first.lesson_id,
            lesson_title=first.lesson.title,
            subject_name=self._subject_name(first),
            total_sessions=total,
            completed_sessions=completed,
            active_sessions=active,
            total_duration_seconds=total_duration,
            average_duration_seconds=average_duration,
            completion_rate=round(
                completion_rate,
                2,
            ),
        )

    async def get_teacher_usage(
        self,
        db: AsyncSession,
        *,
        teacher_id: UUID,
        school_id: UUID | None = None,
    ) -> ALFTeacherUsageResponse:
        sessions = await self.repository.get_all_sessions(
            db,
            school_id=school_id,
            teacher_id=teacher_id,
        )

        if not sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No ALF usage found for this teacher.",
            )

        first = sessions[0]

        total = len(sessions)

        completed = sum(
            session.status == ALFSessionStatus.COMPLETED for session in sessions
        )

        active = sum(
            session.status
            in {
                ALFSessionStatus.STARTED,
                ALFSessionStatus.IN_PROGRESS,
            }
            for session in sessions
        )

        total_duration = sum(session.duration_seconds for session in sessions)

        average_duration = int(total_duration / total) if total else 0

        completion_rate = completed / total * 100 if total else 0

        return ALFTeacherUsageResponse(
            teacher_id=teacher_id,
            teacher_name=self._teacher_name(first),
            total_sessions=total,
            completed_sessions=completed,
            active_sessions=active,
            total_duration_seconds=total_duration,
            average_duration_seconds=average_duration,
            completion_rate=round(
                completion_rate,
                2,
            ),
        )
