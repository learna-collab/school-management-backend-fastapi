from uuid import UUID

from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.school_assignment_repository import (
    school_assignment_repo,
)


class SchoolAssignmentService:
    def __init__(self):
        self.repo = school_assignment_repo

        self.period_repo = DashboardRepository()

        # ==========================================================

    # ACTIVE SESSION / TERM
    # ==========================================================
    # ==========================================================
    # ACTIVE SESSION / TERM
    # ==========================================================

    async def _get_active_period(
        self,
        db,
        school_id: UUID,
    ):
        session = await self.period_repo.get_active_session(
            db,
            school_id,
        )

        term = await self.period_repo.get_active_term(
            db,
            school_id,
        )

        return {
            "session": session,
            "term": term,
            "configured": bool(session and term),
        }

    # ==========================================================
    # SCHOOL STUDENTS
    # ==========================================================

    async def get_school_students(
        self,
        db,
        school_id: UUID,
    ):
        students = await self.repo.get_school_students(
            db,
            school_id,
        )

        return {
            "students": [
                {
                    "id": str(student.id),
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "email": student.email,
                    "class_name": (
                        student.enrollments[0].school_class.name
                        if student.enrollments
                        else None
                    ),
                    "is_active": student.is_active,
                    "username": (
                        student.credential.username if student.credential else None
                    ),
                    "password": (
                        student.credential.password if student.credential else None
                    ),
                }
                for student in students
            ],
            "count": len(students),
        }

    async def get_students_not_in_class(
        self,
        db,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID | None = None,
    ):
        if not session_id:
            period = await self._get_active_period(
                db,
                school_id,
            )

            if not period["configured"]:
                return {
                    "students": [],
                    "count": 0,
                    "requires_academic_setup": True,
                    "message": (
                        "Create and activate an academic session "
                        "and term before assigning students."
                    ),
                }

            session_id = period["session"].id

        students = await self.repo.get_unassigned_students(
            db=db,
            school_id=school_id,
            session_id=session_id,
        )

        return {
            "students": [
                {
                    "id": str(student.id),
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "email": student.email,
                }
                for student in students
            ],
            "count": len(students),
            "requires_academic_setup": False,
        }

    async def get_students(
        self,
        db,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID | None = None,
    ):
        return await self.get_students_not_in_class(
            db=db,
            school_id=school_id,
            class_id=class_id,
            session_id=session_id,
        )

    # ==========================================================
    # SCHOOL TEACHERS
    # ==========================================================

    async def get_school_teachers(
        self,
        db,
        school_id: UUID,
    ):
        teachers = await self.repo.get_school_teachers(
            db,
            school_id,
        )

        return {
            "teachers": [
                {
                    "id": str(teacher.id),
                    "first_name": teacher.first_name,
                    "last_name": teacher.last_name,
                    "email": teacher.email,
                    "class_name": (
                        teacher.class_assignments[0].school_class.name
                        if teacher.class_assignments
                        else None
                    ),
                    "is_active": teacher.is_active,
                    "username": (
                        teacher.credential.username if teacher.credential else None
                    ),
                    "password": (
                        teacher.credential.password if teacher.credential else None
                    ),
                }
                for teacher in teachers
            ],
            "count": len(teachers),
        }

    async def get_teachers_not_in_class(
        self,
        db,
        school_id: UUID,
        class_id: UUID,
    ):
        teachers = await self.repo.get_school_teachers_not_in_class(
            db=db,
            school_id=school_id,
            class_id=class_id,
        )

        return {
            "teachers": [
                {
                    "id": str(teacher.id),
                    "first_name": teacher.first_name,
                    "last_name": teacher.last_name,
                    "email": teacher.email,
                }
                for teacher in teachers
            ],
            "count": len(teachers),
        }

    async def get_teachers(
        self,
        db,
        school_id: UUID,
        class_id: UUID,
    ):
        return await self.get_teachers_not_in_class(
            db=db,
            school_id=school_id,
            class_id=class_id,
        )

    # ==========================================================
    # STUDENT ENROLLMENT
    # ==========================================================

    async def assign_student(
        self,
        db,
        *,
        student_id: UUID,
        class_id: UUID,
        session_id: UUID | None = None,
        school_id: UUID,
    ):
        if not session_id:
            period = await self._get_active_period(
                db,
                school_id,
            )

            if not period["configured"]:
                return {
                    "success": False,
                    "requires_academic_setup": True,
                    "message": (
                        "Create and activate an academic session "
                        "and term before assigning students."
                    ),
                }

            session_id = period["session"].id
        existing = await self.repo.get_student_enrollment(
            db=db,
            student_id=student_id,
            session_id=session_id,
        )

        if existing:
            return {
                "success": False,
                "message": "Student is already assigned to a class for this session.",
            }

        enrollment = await self.repo.assign_student(
            db=db,
            student_id=student_id,
            class_id=class_id,
            session_id=session_id,
            school_id=school_id,
        )

        return {
            "success": True,
            "message": "Student assigned successfully.",
            "enrollment_id": str(enrollment.id),
        }

    async def remove_student_from_class(
        self,
        db,
        *,
        student_id: UUID,
        class_id: UUID,
        session_id: UUID | None = None,
        school_id: UUID | None = None,
    ):
        if not session_id:
            if not school_id:
                return {
                    "success": False,
                    "requires_academic_setup": True,
                    "message": "School ID is required.",
                }

            period = await self._get_active_period(
                db,
                school_id,
            )

            if not period["configured"]:
                return {
                    "success": False,
                    "requires_academic_setup": True,
                    "message": ("No active academic session and term configured."),
                }

            session_id = period["session"].id

        removed = await self.repo.remove_student_from_class(
            db=db,
            student_id=student_id,
            class_id=class_id,
            session_id=session_id,
        )

        return {
            "success": removed,
        }

    # ==========================================================
    # TEACHER SUBJECT ASSIGNMENT
    # ==========================================================
    async def assign_teacher_to_class(
        self,
        db,
        *,
        teacher_id: UUID,
        class_id: UUID,
        school_id: UUID,
    ):
        assignment = await self.repo.assign_teacher_to_class(
            db=db,
            teacher_id=teacher_id,
            class_id=class_id,
            school_id=school_id,
        )

        return {
            "message": "Teacher assigned successfully",
            "assignment_id": str(assignment.id),
        }

    async def assign_teacher(
        self,
        db,
        *,
        teacher_id: UUID,
        class_id: UUID,
        subject_id: UUID,
        school_id: UUID,
    ):
        assignment = await self.repo.assign_teacher(
            db=db,
            teacher_id=teacher_id,
            class_id=class_id,
            subject_id=subject_id,
            school_id=school_id,
        )

        return {
            "message": "Teacher assigned successfully.",
            "assignment_id": str(assignment.id),
        }

    async def remove_teacher_assignment(
        self,
        db,
        *,
        teacher_id: UUID,
        class_id: UUID,
        subject_id: UUID,
    ):
        removed = await self.repo.remove_teacher_assignment(
            db=db,
            teacher_id=teacher_id,
            class_id=class_id,
            subject_id=subject_id,
        )

        return {
            "success": removed,
        }

    async def remove_teacher_from_class(
        self,
        db,
        *,
        teacher_id: UUID,
        class_id: UUID,
    ):
        removed = await self.repo.remove_teacher_from_class(
            db=db,
            teacher_id=teacher_id,
            class_id=class_id,
        )

        return {
            "success": removed,
            "message": (
                "Teacher removed from class"
                if removed
                else "Teacher not assigned to class"
            ),
        }

    # ==========================================================
    # CLASS MEMBERS
    # ==========================================================

    async def get_class_students(
        self,
        db,
        class_id: UUID,
        session_id: UUID | None = None,
        school_id: UUID | None = None,
    ):
        if not session_id:
            if not school_id:
                return {
                    "students": [],
                    "count": 0,
                    "requires_academic_setup": True,
                    "message": ("School ID is required when session is not supplied."),
                }

            period = await self._get_active_period(
                db,
                school_id,
            )

            if not period["configured"]:
                return {
                    "students": [],
                    "count": 0,
                    "requires_academic_setup": True,
                    "message": (
                        "Create and activate an academic session "
                        "and term before viewing class students."
                    ),
                }

            session_id = period["session"].id

        students = await self.repo.get_class_students(
            db=db,
            class_id=class_id,
            session_id=session_id,
        )

        return {
            "students": [
                {
                    "id": str(student.id),
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "email": student.email,
                }
                for student in students
            ],
            "count": len(students),
            "requires_academic_setup": False,
        }

    async def get_class_teachers(
        self,
        db,
        class_id: UUID,
    ):
        teachers = await self.repo.get_class_teachers(
            db=db,
            class_id=class_id,
        )

        return {
            "teachers": [
                {
                    "id": str(teacher.id),
                    "first_name": teacher.first_name,
                    "last_name": teacher.last_name,
                    "email": teacher.email,
                }
                for teacher in teachers
            ],
            "count": len(teachers),
        }

    async def get_class_assignments(
        self,
        db,
        class_id: UUID,
    ):
        assignments = await self.repo.get_class_assignments(
            db=db,
            class_id=class_id,
        )

        return {
            "assignments": [
                {
                    "assignment_id": str(item.id),
                    "teacher_id": str(item.teacher.user.id),
                    "teacher_name": (
                        f"{item.teacher.user.first_name} {item.teacher.user.last_name}"
                    ),
                    "subject_id": str(item.subject.id),
                    "subject_name": item.subject.name,
                }
                for item in assignments
            ],
            "count": len(assignments),
        }

    async def promote_students(
        self,
        db,
        *,
        from_class_id: UUID,
        to_class_id: UUID,
        from_session_id: UUID,
        to_session_id: UUID,
    ):
        promoted = await self.repo.promote_students(
            db=db,
            from_class_id=from_class_id,
            to_class_id=to_class_id,
            from_session_id=from_session_id,
            to_session_id=to_session_id,
        )

        return {
            "message": "Students promoted successfully.",
            "students_promoted": promoted,
        }


school_assignment_service = SchoolAssignmentService()
