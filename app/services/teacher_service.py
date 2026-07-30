from fastapi import HTTPException

from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.teacher_assignment_repository import teacher_assignment_repository


class TeacherService:
    def __init__(self):
        self.repo = teacher_assignment_repository
        self.session_repo = DashboardRepository()

    async def get_classes(
        self,
        db,
        teacher,
    ):
        assignments = await self.repo.get_teacher_classes(
            db,
            teacher.id,
        )

        unique_classes = {}

        for item in assignments:
            class_id = str(item.class_id)

            if class_id not in unique_classes:
                unique_classes[class_id] = {
                    "id": class_id,
                    "name": item.school_class.name,
                }

        return list(unique_classes.values())

    async def get_class_students(self, db, user, class_id, school_id):
        has_access = await self.repo.teacher_has_class_access(
            db=db,
            teacher_id=user.id,
            class_id=class_id,
        )

        if not has_access:
            raise ValueError("You are not assigned to this class")

        active_session = await self.session_repo.get_active_session(
            db,
            user.school_id,
        )

        active_term = await self.session_repo.get_active_term(
            db,
            user.school_id,
        )

        students = await self.repo.get_students_by_class(
            db=db,
            class_id=class_id,
            session_id=active_session.id,
            term_id=active_term.id,
        )

        return [
            {
                "id": str(student.user.id),
                "first_name": student.user.first_name,
                "last_name": student.user.last_name,
                "email": student.user.email,
                "admission_number": student.admission_number,
            }
            for student in students
        ]

    async def get_subjects(
        self,
        db,
        teacher,
        class_id,
    ):
        access = await self.repo.teacher_has_class_access(
            db,
            teacher.id,
            class_id,
        )

        if not access:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this class",
            )

        assignments = await self.repo.get_class_subjects(
            db,
            class_id,
        )

        unique_subjects = {}

        for item in assignments:
            subject_id = str(item.subject_id)

            if subject_id not in unique_subjects:
                unique_subjects[subject_id] = {
                    "id": subject_id,
                    "name": item.subject.name,
                }

        return list(unique_subjects.values())


teacher_service = TeacherService()
