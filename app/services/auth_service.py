import secrets
from datetime import UTC, datetime, timedelta

from app.models.password_reset import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.email_service import email_service
from app.services.user_service import UserService
from app.utils.helper import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class AuthService:
    def __init__(self):
        self.user_service = UserService()
        self.refresh_repo = RefreshTokenRepository()
        self.email_service = email_service

    async def register(
        self,
        db,
        username: str,
        email: str,
        password: str,
    ):
        school_slug, actual_username = username.split("_", 1)
        school = await self.user_service.get_school_by_slug(
            db,
            school_slug,
        )

        if not school:
            return None

        existing_email = await self.user_service.get_by_email(
            db,
            email,
        )

        if existing_email:
            return None

        existing_username = await self.user_service.get_by_school_slug_and_username(
            db,
            school_slug,
            actual_username,
        )

        if existing_username:
            return None

        user = await self.user_service.create_user_with_profile(
            db=db,
            username=actual_username,
            email=email,
            password=hash_password(password),
            role="STUDENT",  # default role
            school_id=school.id,
        )

        return user

    async def login(
        self,
        db,
        username: str,
        password: str,
    ):
        user = None

        # -----------------------------------
        # SCHOOL ADMIN / SUPER ADMIN
        # login without school slug
        # Example:
        # superadmin
        # schooladmin
        # -----------------------------------
        if "_" not in username:
            user = await self.user_service.get_by_email(
                db,
                username,
            )

            if not user:
                return None

        # -----------------------------------
        # STUDENTS / TEACHERS / PARENTS
        # Example:
        # lerna_john
        # -----------------------------------
        else:
            school_slug, actual_username = username.split("_", 1)

            user = await self.user_service.get_by_school_slug_and_username(
                db,
                school_slug,
                actual_username,
            )

            if not user:
                return None

        # -----------------------------------
        # VERIFY PASSWORD
        # -----------------------------------
        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        # -----------------------------------
        # CREATE TOKENS
        # -----------------------------------
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role,
                "school_id": (str(user.school_id) if user.school_id else None),
            }
        )

        refresh_token = create_refresh_token()

        refresh_db = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(
                refresh_token,
            ),
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        await self.refresh_repo.create(
            db,
            refresh_db,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "school_id": (str(user.school_id) if user.school_id else None),
                "school_name": (user.school.name if user.school else None),
                "school_logo": (user.school.logo_url if user.school else None),
                "profile_completed": user.profile_completed,
            },
        }

    async def forgot_password(self, db, email: str):
        user = await self.user_service.get_by_email(db, email)

        if not user:
            return True  # avoid email enumeration attacks

        token = secrets.token_urlsafe(32)

        reset = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )

        db.add(reset)
        await db.commit()

        reset_link = f"http://localhost:3000/reset-password?token={token}"

        await self.email_service.send_email(
            to=user.email,
            subject="Password Reset",
            body=f"Click to reset password: {reset_link}",
        )

        return True

    async def reset_password(self, db, token: str, new_password: str):
        result = await db.execute(
            """
            SELECT * FROM password_reset_tokens
            WHERE token = :token
            """,
            {"token": token},
        )

        reset = result.scalar_one_or_none()

        if not reset:
            return False

        if reset.used:
            return False

        if reset.expires_at < datetime.now(UTC):
            return False

        user = await self.user_service.get_by_id(
            db,
            reset.user_id,
        )

        if not user:
            return False

        user.password = hash_password(new_password)

        reset.used = True

        await db.commit()

        return True

    async def refresh_access_token(
        self,
        db,
        refresh_token: str,
    ):
        token_record = await self.refresh_repo.get_by_hash(
            db,
            hash_refresh_token(refresh_token),
        )

        if not token_record:
            return None

        if token_record.revoked:
            return None

        if token_record.expires_at < datetime.now(UTC):
            return None

        user = await self.user_service.get_by_id(
            db,
            token_record.user_id,
        )

        if not user:
            return None

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role,
                "school_id": str(user.school_id),
            }
        )

        return access_token


authservice = AuthService()
