from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums.alf import ALFSessionStatus
from app.models.lesson import Lesson
from app.models.teacher_alf_session import TeacherALFSession
from app.models.user import User


class TeacherALFUsageRepository:
    def _base_query(self):
        return (
            select(TeacherALFSession)
            .join(
                User,
                User.id == TeacherALFSession.teacher_id,
            )
            .options(
                selectinload(TeacherALFSession.teacher),
                selectinload(TeacherALFSession.lesson).selectinload(
                    Lesson.subject_template
                ),
                selectinload(TeacherALFSession.school_class),
            )
        )

    async def get_all_sessions(
        self,
        db: AsyncSession,
        *,
        school_id: UUID | None = None,
        teacher_id: UUID | None = None,
        lesson_id: UUID | None = None,
        class_id: UUID | None = None,
        status: ALFSessionStatus | None = None,
    ) -> list[TeacherALFSession]:
        query = self._base_query()

        if school_id is not None:
            query = query.where(User.school_id == school_id)

        if teacher_id is not None:
            query = query.where(TeacherALFSession.teacher_id == teacher_id)

        if lesson_id is not None:
            query = query.where(TeacherALFSession.lesson_id == lesson_id)

        if class_id is not None:
            query = query.where(TeacherALFSession.class_id == class_id)

        if status is not None:
            query = query.where(TeacherALFSession.status == status)

        query = query.order_by(TeacherALFSession.started_at.desc())

        result = await db.execute(query)

        return list(result.scalars().all())

    async def get_session(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        school_id: UUID | None = None,
    ) -> TeacherALFSession | None:
        query = self._base_query().where(TeacherALFSession.id == session_id)

        if school_id is not None:
            query = query.where(User.school_id == school_id)

        result = await db.execute(query)

        return result.scalar_one_or_none()

    async def get_stats(
        self,
        db: AsyncSession,
        *,
        school_id: UUID | None = None,
    ) -> dict:
        query = (
            select(
                func.count(TeacherALFSession.id),
                func.coalesce(
                    func.sum(TeacherALFSession.duration_seconds),
                    0,
                ),
                func.coalesce(
                    func.avg(TeacherALFSession.duration_seconds),
                    0,
                ),
            )
            .select_from(TeacherALFSession)
            .join(
                User,
                User.id == TeacherALFSession.teacher_id,
            )
        )

        if school_id is not None:
            query = query.where(User.school_id == school_id)

        total_result = await db.execute(query)

        total_sessions, total_duration, average_duration = total_result.one()

        status_query = (
            select(
                TeacherALFSession.status,
                func.count(TeacherALFSession.id),
            )
            .select_from(TeacherALFSession)
            .join(
                User,
                User.id == TeacherALFSession.teacher_id,
            )
        )

        if school_id is not None:
            status_query = status_query.where(User.school_id == school_id)

        status_query = status_query.group_by(TeacherALFSession.status)

        status_result = await db.execute(status_query)

        status_counts = dict(status_result.all())

        completed_sessions = status_counts.get(
            ALFSessionStatus.COMPLETED,
            0,
        )

        total_sessions = int(total_sessions or 0)

        completion_rate = (
            completed_sessions / total_sessions * 100 if total_sessions else 0
        )

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "in_progress_sessions": status_counts.get(
                ALFSessionStatus.IN_PROGRESS,
                0,
            ),
            "started_sessions": status_counts.get(
                ALFSessionStatus.STARTED,
                0,
            ),
            "abandoned_sessions": status_counts.get(
                ALFSessionStatus.ABANDONED,
                0,
            ),
            "total_duration_seconds": int(total_duration or 0),
            "average_duration_seconds": int(float(average_duration or 0)),
            "completion_rate": round(
                completion_rate,
                2,
            ),
        }
