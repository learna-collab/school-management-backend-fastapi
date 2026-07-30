from uuid import UUID

from fastapi import HTTPException, status

from app.models.classes import Class
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.school_class_repository import school_class_repository
from app.schemas.teacher_assignmet import CreateClassRequest


class SchoolClassService:
    def __init__(self):
        self.repo = school_class_repository
        self.session_repo = DashboardRepository()

    # ==========================================================
    # CREATE CLASS
    # ==========================================================

    async def create_class(
        self,
        db,
        data: CreateClassRequest,
        school_id: UUID,
    ):
        cls = Class(
            name=data.name,
            level=data.level,
            school_id=school_id,
        )

        return await self.repo.create(
            db,
            cls,
        )

    # ==========================================================
    # GET SCHOOL CLASSES
    # ==========================================================

    async def get_classes(
        self,
        db,
        school_id: UUID,
    ):
        return await self.repo.get_by_school(
            db,
            school_id,
        )

    # ==========================================================
    # DELETE CLASS
    # ==========================================================

    async def delete_class(
        self,
        db,
        class_id: UUID,
    ):
        deleted = await self.repo.delete(
            db,
            class_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found.",
            )

        return {
            "message": "Class deleted successfully.",
        }

    # ==========================================================
    # CLASS DASHBOARD
    # ==========================================================

    async def get_class_dashboard(self, db, class_id: UUID, school_id):
        print("school_id=========================", school_id)
        active_session = await self.session_repo.get_active_session(db, school_id)

        active_term = await self.session_repo.get_active_term(db, school_id)

        if not active_session or not active_term:
            dashboard = await self.repo.get_class_basic_info(
                db,
                class_id,
            )

            dashboard["active_session"] = None
            dashboard["active_term"] = None

            dashboard["students_count"] = 0
            dashboard["teachers_count"] = 0
            dashboard["subjects_count"] = 0
            dashboard["attendance_rate"] = 0

            return dashboard

        dashboard = await self.repo.get_class_dashboard(
            db=db,
            class_id=class_id,
            session_id=active_session.id,
        )

        if not dashboard:
            raise HTTPException(
                status_code=404,
                detail="Class not found",
            )

        dashboard["active_session"] = {
            "id": str(active_session.id),
            "name": active_session.name,
        }

        dashboard["active_term"] = {
            "id": str(active_term.id),
            "name": active_term.name,
        }

        return dashboard


school_class_service = SchoolClassService()
