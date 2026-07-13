from app.repositories.school_admin_dashboard_repository import (
    SchoolAdminDashboardRepository,
)


class SchoolAdminDashboardService:
    def __init__(self):
        self.repo = SchoolAdminDashboardRepository()

    async def dashboard(
        self,
        db,
        current_user,
    ):
        school_id = current_user.school_id

        students = await self.repo.count_students(
            db,
            school_id,
        )

        teachers = await self.repo.count_teachers(
            db,
            school_id,
        )

        parents = await self.repo.count_parents(
            db,
            school_id,
        )

        classes = await self.repo.count_classes(
            db,
            school_id,
        )

        subjects = await self.repo.count_subjects(
            db,
            school_id,
        )

        session = await self.repo.get_active_session(db, school_id)

        term = await self.repo.get_active_term(db, school_id)

        attendance = await self.repo.attendance_summary(
            db,
            school_id,
        )

        total_batches = await self.repo.count_result_batches(
            db,
            school_id,
        )

        approved_batches = await self.repo.count_approved_batches(
            db,
            school_id,
        )

        pending_batches = await self.repo.count_pending_batches(
            db,
            school_id,
        )

        published_batches = await self.repo.count_published_batches(
            db,
            school_id,
        )

        recent_students = await self.repo.latest_students(
            db,
            school_id,
        )

        recent_teachers = await self.repo.latest_teachers(
            db,
            school_id,
        )
        school = await self.repo.get_school(
            db,
            current_user.school_id,
        )

        return {
            "school_name": school.name if school else "School",
            "active_session": {
                "id": str(session.id),
                "name": session.name,
            }
            if session
            else None,
            "active_term": {
                "id": str(term.id),
                "name": term.name,
            }
            if term
            else None,
            "overview": {
                "students": students,
                "teachers": teachers,
                "parents": parents,
                "classes": classes,
                "subjects": subjects,
            },
            "attendance": attendance,
            "results": {
                "total_batches": total_batches,
                "approved_batches": approved_batches,
                "pending_batches": pending_batches,
                "published_batches": published_batches,
            },
            "recent_students": [
                {
                    "id": str(student.id),
                    "name": f"{student.first_name} {student.last_name}",
                    "email": student.email,
                }
                for student in recent_students
            ],
            "recent_teachers": [
                {
                    "id": str(teacher.id),
                    "name": f"{teacher.first_name} {teacher.last_name}",
                    "email": teacher.email,
                }
                for teacher in recent_teachers
            ],
        }


school_admin_dashboard_service = SchoolAdminDashboardService()
