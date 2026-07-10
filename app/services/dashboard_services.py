from app.repositories.dashboard_repository import (
    DashboardRepository,
)


class DashboardService:
    def __init__(self):
        self.repo = DashboardRepository()

    # ==========================================
    # STUDENT DASHBOARD
    # ==========================================

    async def student_dashboard(
        self,
        db,
        user,
    ):
        profile = await self.repo.get_student_profile(
            db,
            user.id,
        )

        attendance = await self.repo.get_student_attendance_stats(
            db,
            user.id,
        )

        enrollment = await self.repo.get_current_student_enrollment(
            db,
            user.id,
        )

        summary = await self.repo.get_student_latest_summary(
            db,
            user.id,
        )

        total = attendance["present"] + attendance["absent"] + attendance["late"]

        rate = (
            round(
                (attendance["present"] / total) * 100,
                2,
            )
            if total
            else 0
        )

        session = await self.repo.get_active_session(db)
        term = await self.repo.get_active_term(db)

        return {
            "student_name": f"{user.first_name} {user.last_name}",
            "admission_number": (profile.admission_number if profile else None),
            "class_name": (enrollment.school_class.name if enrollment else None),
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
            "attendance": {
                **attendance,
                "attendance_rate": rate,
            },
            "average_score": (summary.average_score if summary else 0),
            "position": (summary.position if summary else None),
        }

    # ==========================================
    # TEACHER DASHBOARD
    # ==========================================

    async def teacher_dashboard(
        self,
        db,
        user,
    ):
        classes = await self.repo.get_teacher_classes(
            db,
            user.id,
        )

        subject_assignments = await self.repo.get_teacher_subject_assignments(
            db,
            user.id,
        )

        attendance_submissions = await self.repo.count_teacher_attendance(
            db,
            user.id,
        )

        results_submitted = await self.repo.count_teacher_results(
            db,
            user.id,
        )

        lessons_created = await self.repo.count_teacher_lessons(
            db,
            user.id,
        )

        session = await self.repo.get_active_session(db)
        term = await self.repo.get_active_term(db)

        return {
            "teacher_name": f"{user.first_name} {user.last_name}",
            "active_session": (
                {
                    "id": str(session.id),
                    "name": session.name,
                }
                if session
                else None
            ),
            "active_term": (
                {
                    "id": str(term.id),
                    "name": term.name,
                }
                if term
                else None
            ),
            "assigned_classes": len(classes),
            "assigned_subjects": len({str(x.subject_id) for x in subject_assignments}),
            "lessons_created": lessons_created or 0,
            "attendance_submissions": attendance_submissions or 0,
            "results_submitted": results_submitted or 0,
            "classes": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "level": row["level"],
                    "students_count": row["students_count"],
                    "subjects_count": row["subjects_count"],
                }
                for row in classes
            ],
            "subject_assignments": [
                {
                    "class_id": str(x.class_id),
                    "subject_id": str(x.subject_id),
                    "class_name": x.school_class.name,
                    "subject_name": x.subject.name,
                }
                for x in subject_assignments
            ],
        }

    # ==========================================
    # TEACHER CLASSES
    # ==========================================

    async def get_classes(
        self,
        db,
        user,
    ):
        rows = await self.repo.get_teacher_classes(db, user.id)

        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "level": row["level"],
                "students_count": row["students_count"],
                "subjects_count": row["subjects_count"],
            }
            for row in rows
        ]


dashboard_service = DashboardService()
