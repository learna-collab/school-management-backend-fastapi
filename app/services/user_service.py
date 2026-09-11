from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.profile_service import ProfileService
from app.utils.helper import hash_password


class UserService:
    def __init__(self):
        self.repo = UserRepository()
        self.profile_service = ProfileService()

    # =====================================
    # CREATE USER + PROFILE
    # =====================================

    async def create_user_with_profile(
        self,
        db,
        email: str,
        password: str,
        role,
        school_id: str,
        username: str,
        *,
        profile_completed: bool = False,
    ):
        user = User(
            email=email,
            password_hash=password,
            role=role,
            school_id=school_id,
            username=username,
            profile_completed=profile_completed,
        )

        user = await self.repo.create(db, user)

        return user

    # =====================================
    # CREATE VENDOR USER
    # =====================================

    async def create_vendor_user(
        self,
        db,
        email: str,
        password: str,
        username: str,
    ):
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.VENDOR,
            school_id=None,
            username=username,
            profile_completed=False,
        )

        user = await self.repo.create(db, user)

        return user

    # =====================================
    # GET SCHOOL BY SLUG
    # =====================================

    async def get_school_by_slug(
        self,
        db,
        slug: str,
    ):
        return await self.repo.get_school_by_slug(
            db,
            slug,
        )

    # =====================================
    # GET USER BY EMAIL
    # =====================================

    async def get_by_email(
        self,
        db,
        email: str,
    ):
        return await self.repo.get_by_email(
            db,
            email,
        )

    # =====================================
    # GET USER BY ID
    # =====================================

    async def get_by_id(
        self,
        db,
        user_id: str,
    ):
        return await self.repo.get_by_id(
            db,
            user_id,
        )

    async def get_by_username(
        self,
        db,
        username: str,
    ):
        return await self.repo.get_by_username(
            db,
            username,
        )

    # =====================================
    # GET ALL USERS
    # =====================================

    async def get_all_users(
        self,
        db,
    ):
        return await self.repo.get_all(db)

    async def get_by_school_slug_and_username(
        self,
        db,
        school_slug: str,
        username: str,
    ):
        return await self.repo.get_by_school_slug_and_username(
            db,
            school_slug,
            username,
        )

    # =====================================
    # DELETE USER
    # =====================================

    async def delete_user(
        self,
        db,
        user_id: str,
    ):
        user = await self.repo.get_by_id(
            db,
            user_id,
        )

        if not user:
            return None

        await self.repo.delete(
            db,
            user,
        )

        return True


userservice = UserService()
