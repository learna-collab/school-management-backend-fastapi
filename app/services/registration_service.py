import re
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy import func, select

from app.models.user import User
from app.models.user_credentials import UserCredential
from app.repositories.registration_repository import registration_repo
from app.schemas.registration import (
    ParentRegistrationCreate,
    StudentRegistrationCreate,
    TeacherRegistrationCreate,
)
from app.services.profile_service import ProfileService
from app.services.school_service import SchoolService
from app.services.user_service import UserService
from app.utils.helper import hash_password


class RegistrationService:
    def __init__(self):
        self.repo = registration_repo
        self.user_service = UserService()
        self.profile_service = ProfileService()
        self.school_service = (
            SchoolService()
        )  # Assuming school_service is part of user_service for this context

    # =====================================================
    # PASSWORD GENERATOR
    # =====================================================

    def generate_school_prefix(self, school_name: str) -> str:
        """
        Examples.

        Lerna International School -> LIS
        Government Secondary School -> GSS
        Federal Government College -> FGC
        Queen's College -> QUC
        Green Valley Academy -> GVA
        King's High School -> KHS
        """
        words = re.findall(r"[A-Za-z]+", school_name.upper())

        if not words:
            return "SCH"

        # Multiple words -> first letter of first 3 words
        if len(words) >= 3:
            return "".join(word[0] for word in words[:3])

        # Two words
        if len(words) == 2:
            first, second = words
            return (first[:2] + second[:1]).ljust(3, "X")

        # One word
        return words[0][:3].ljust(3, "X")

    async def generate_username(
        self,
        db,
        school,
    ) -> str:
        prefix = self.generate_school_prefix(school.name)

        total_users = await db.scalar(
            select(func.count(User.id)).where(
                User.school_id == school.id,
            )
        )

        next_number = (total_users or 0) + 1

        return f"{prefix}-{next_number:06d}"

    def generate_password(self, length: int = 10):
        alphabet = string.ascii_letters + string.digits

        password = "".join(secrets.choice(alphabet) for _ in range(length))

        return password

    # =====================================================
    # COMMON USER CREATION
    # =====================================================

    async def _create_user(
        self,
        db,
        school_id,
        role,
        email,
    ):
        # Email must be unique
        exists = await self.repo.email_exists(
            db,
            email,
        )

        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{email} already exists.",
            )

        school = await self.school_service.get_by_id(
            db,
            school_id,
        )

        username = await self.generate_username(
            db,
            school,
        )

        password = self.generate_password()

        user = await self.user_service.create_user_with_profile(
            db=db,
            email=email,
            password=hash_password(password),
            role=role,
            school_id=school_id,
            username=username,
            profile_completed=True,
        )

        credential = UserCredential(
            school_id=school_id,
            user_id=user.id,
            username=username,
            password=password,
        )

        await self.repo.save(
            db,
            credential,
        )

        return user, username, password

    # =====================================================
    # REGISTER STUDENT
    # =====================================================

    async def register_student(
        self,
        db,
        school_id,
        payload: StudentRegistrationCreate,
    ):
        cls = await self.repo.get_class(
            db,
            payload.class_id,
        )

        if not cls:
            raise HTTPException(
                status_code=404,
                detail="Class not found.",
            )

        user, username, password = await self._create_user(
            db=db,
            school_id=school_id,
            role="STUDENT",
            email=payload.email,
        )

        await self.profile_service.create_profile(
            db=db,
            user=user,
            payload={
                "role": "STUDENT",
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "gender": payload.gender,
                "date_of_birth": payload.date_of_birth,
                "admission_date": payload.admission_date,
                "class_id": payload.class_id,
            },
        )

        return {
            "username": username,
            "password": password,
            "user": user,
        }

    # =====================================================
    # REGISTER TEACHER
    # =====================================================

    async def register_teacher(
        self,
        db,
        school_id,
        payload: TeacherRegistrationCreate,
    ):
        cls = await self.repo.get_class(
            db,
            payload.class_id,
        )

        if not cls:
            raise HTTPException(
                status_code=404,
                detail="Class not found.",
            )

        user, username, password = await self._create_user(
            db=db,
            school_id=school_id,
            role="TEACHER",
            email=payload.email,
        )

        await self.profile_service.create_profile(
            db=db,
            user=user,
            payload={
                "role": "TEACHER",
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "qualification": payload.qualification,
                "specialization": payload.specialization,
                "hire_date": payload.hire_date,
                "class_id": payload.class_id,
            },
        )

        return {
            "username": username,
            "password": password,
            "user": user,
        }

    # =====================================================
    # REGISTER PARENT
    # =====================================================

    async def register_parent(
        self,
        db,
        school_id,
        payload: ParentRegistrationCreate,
    ):
        user, username, password = await self._create_user(
            db=db,
            school_id=school_id,
            role="PARENT",
            email=payload.email,
        )

        await self.profile_service.create_profile(
            db=db,
            user=user,
            payload={
                "role": "PARENT",
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "occupation": payload.occupation,
                "phone": payload.phone,
            },
        )

        return {
            "username": username,
            "password": password,
            "user": user,
        }

        # =====================================================

    # BATCH STUDENT REGISTRATION
    # =====================================================

    async def register_students_batch(
        self,
        db,
        school_id,
        payloads: list[StudentRegistrationCreate],
    ):
        users = []

        for payload in payloads:
            result = await self.register_student(
                db=db,
                school_id=school_id,
                payload=payload,
            )

            users.append(
                {
                    "name": f"{payload.first_name} {payload.last_name}",
                    "username": result["username"],
                    "password": result["password"],
                }
            )

        return users

    # =====================================================
    # BATCH TEACHER REGISTRATION
    # =====================================================

    async def register_teachers_batch(
        self,
        db,
        school_id,
        payloads: list[TeacherRegistrationCreate],
    ):
        users = []

        for payload in payloads:
            result = await self.register_teacher(
                db=db,
                school_id=school_id,
                payload=payload,
            )

            users.append(
                {
                    "name": f"{payload.first_name} {payload.last_name}",
                    "username": result["username"],
                    "password": result["password"],
                }
            )

        return users

    # =====================================================
    # BATCH PARENT REGISTRATION
    # =====================================================

    async def register_parents_batch(
        self,
        db,
        school_id,
        payloads: list[ParentRegistrationCreate],
    ):
        users = []

        for payload in payloads:
            result = await self.register_parent(
                db=db,
                school_id=school_id,
                payload=payload,
            )

            users.append(
                {
                    "name": f"{payload.first_name} {payload.last_name}",
                    "username": result["username"],
                    "password": result["password"],
                }
            )

        return users


registration_service = RegistrationService()
