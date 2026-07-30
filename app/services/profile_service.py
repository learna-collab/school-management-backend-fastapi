import random
from datetime import datetime

from app.models.user import UserRole
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profiles import (
    ParentProfileCreate,
    ParentProfileUpdate,
    StudentProfileCreate,
    StudentProfileUpdate,
    TeacherProfileCreate,
    TeacherProfileUpdate,
)
from app.services.school_assignment_service import school_assignment_service

ALLOWED_PROFILE_ROLES = {
    UserRole.STUDENT,
    UserRole.TEACHER,
    UserRole.PARENT,
}


class ProfileService:
    def __init__(self):
        self.repo = ProfileRepository()
        self.session_repo = DashboardRepository()
        self.school_assignment_service = school_assignment_service

    # =====================================================
    # GET PROFILE
    # =====================================================
    def generate_employee_id(
        self,
        school_code: str | None = None,
    ) -> str:
        year = datetime.utcnow().year

        unique_part = random.randint(
            10000,
            99999,
        )

        if school_code:
            return f"{school_code[:3].upper()}-EMP-{year}-{unique_part}"

        return f"EMP-{year}-{unique_part}"

    def generate_admission_number(self, school_code: str | None = None) -> str:
        year = datetime.utcnow().year

        # 6-digit random number (safe enough for most school systems)
        unique_part = random.randint(100000, 999999)

        if school_code:
            return f"{school_code[:3].upper()}/{year}/{unique_part}"

        return f"SCH/{year}/{unique_part}"

    async def get_by_user_id(self, db, user):
        if user.role == UserRole.STUDENT:
            return await self.repo.get_student(db, user.id)

        if user.role == UserRole.TEACHER:
            return await self.repo.get_teacher(db, user.id)

        if user.role == UserRole.PARENT:
            return await self.repo.get_parent(db, user.id)

        return None

    # =====================================================
    # UPDATE PROFILE (ROLE-SCHEMA VALIDATION)
    # =====================================================
    # =====================================================
    # UPDATE PROFILE (ROLE-SCHEMA VALIDATION)
    # =====================================================
    async def update_profile(self, db, user, payload: dict):
        # ==========================================
        # UPDATE USER BASIC INFO
        # ==========================================
        first_name = payload.pop("first_name", None)
        last_name = payload.pop("last_name", None)

        if first_name is not None:
            user.first_name = first_name.strip()

        if last_name is not None:
            user.last_name = last_name.strip()

        db.add(user)

        profile = None

        # ==========================================
        # STUDENT
        # ==========================================
        if user.role == UserRole.STUDENT:
            data = StudentProfileUpdate(**payload)

            profile = await self.repo.get_student(
                db,
                user.id,
            )

            if not profile:
                return None

            for key, value in data.model_dump(
                exclude_unset=True,
            ).items():
                setattr(profile, key, value)

        # ==========================================
        # TEACHER
        # ==========================================
        elif user.role == UserRole.TEACHER:
            data = TeacherProfileUpdate(**payload)

            profile = await self.repo.get_teacher(
                db,
                user.id,
            )

            if not profile:
                return None

            for key, value in data.model_dump(
                exclude_unset=True,
            ).items():
                setattr(profile, key, value)

        # ==========================================
        # PARENT
        # ==========================================
        elif user.role == UserRole.PARENT:
            data = ParentProfileUpdate(**payload)

            profile = await self.repo.get_parent(
                db,
                user.id,
            )

            if not profile:
                return None

            for key, value in data.model_dump(
                exclude_unset=True,
            ).items():
                setattr(profile, key, value)

        else:
            return None

        db.add(profile)

        await db.commit()

        await db.refresh(user)
        await db.refresh(profile)

        return {
            "user": user,
            "profile": profile,
        }

    async def create_profile(
        self,
        db,
        user,
        payload: dict,
    ):
        # ==========================================
        # UPDATE USER BASIC INFO
        # ==========================================
        first_name = payload.pop("first_name", None)
        last_name = payload.pop("last_name", None)
        class_id = payload.pop("class_id", None)

        if first_name:
            user.first_name = first_name.strip()

        if last_name:
            user.last_name = last_name.strip()

        # ==========================================
        # ROLE SELECTION FROM FRONTEND
        # ==========================================
        selected_role = payload.pop("role", None)

        if selected_role:
            try:
                role = UserRole(selected_role)

            except ValueError as err:
                raise ValueError(
                    "Invalid role selected",
                ) from err

            if role not in ALLOWED_PROFILE_ROLES:
                raise ValueError(
                    "Only STUDENT, TEACHER and PARENT profiles can be created",
                )

            user.role = role

        profile = None

        # ==========================================
        # STUDENT
        # ==========================================
        if user.role == UserRole.STUDENT:
            admission_number = self.generate_admission_number(
                str(user.school_id),
            )

            data = StudentProfileCreate(
                admission_number=admission_number,
                **payload,
            )

            profile = await self.repo.create_student(
                db=db,
                data=data,
                user_id=user.id,
                school_id=user.school_id,
            )

            if class_id:
                active_session = await self.session_repo.get_active_session(
                    db,
                    user.school_id,
                )

                if active_session:
                    await self.school_assignment_service.assign_student(
                        db=db,
                        student_id=user.id,
                        class_id=class_id,
                        session_id=active_session.id,
                        school_id=user.school_id,
                    )

        # ==========================================
        # TEACHER
        # ==========================================
        elif user.role == UserRole.TEACHER:
            employee_id = self.generate_employee_id(
                str(user.school_id),
            )

            data = TeacherProfileCreate(
                employee_id=employee_id,
                **payload,
            )

            profile = await self.repo.create_teacher(
                db=db,
                data=data,
                user_id=user.id,
                school_id=user.school_id,
            )

            if class_id:
                assignment = (
                    await self.school_assignment_service.assign_teacher_to_class(
                        db=db,
                        teacher_id=user.id,
                        class_id=class_id,
                        school_id=user.school_id,
                    )
                )

                print("response ========================")
                print(assignment)
                print("response ========================")

        # ==========================================
        # PARENT
        # ==========================================
        elif user.role == UserRole.PARENT:
            data = ParentProfileCreate(
                **payload,
            )

            profile = await self.repo.create_parent(
                db=db,
                data=data,
                user_id=user.id,
                school_id=user.school_id,
            )

        else:
            raise ValueError(
                "Unsupported role",
            )

        # ==========================================
        # MARK COMPLETE
        # ==========================================
        user.profile_completed = True

        db.add(user)

        await db.commit()

        await db.refresh(user)

        return {
            "profile": profile,
            "user": user,
        }
