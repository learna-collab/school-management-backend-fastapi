import math

from app.repositories.directory.directory_repository import DirectorySchoolRepository


class DirectorySchoolService:
    def __init__(self):
        self.repo = DirectorySchoolRepository()

    # =====================================================
    # PUBLIC SCHOOL LIST
    # =====================================================

    async def list_schools(
        self,
        db,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        state: str | None = None,
        city: str | None = None,
        school_type: str | None = None,
        ownership_type: str | None = None,
        verified: bool | None = None,
    ):
        schools, total = await self.repo.get_public_schools(
            db,
            page=page,
            page_size=page_size,
            search=search,
            state=state,
            city=city,
            school_type=school_type,
            ownership_type=ownership_type,
            verified=verified,
        )

        total_pages = math.ceil(total / page_size) if total else 0

        return {
            "items": schools,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # PUBLIC SCHOOL DETAILS
    # =====================================================

    async def get_school_by_slug(
        self,
        db,
        slug: str,
    ):
        return await self.repo.get_public_by_slug(
            db,
            slug,
        )

    # =====================================================
    # FEATURED
    # =====================================================

    async def get_featured(
        self,
        db,
        limit: int = 12,
    ):
        return await self.repo.get_featured(
            db,
            limit,
        )

    # =====================================================
    # VERIFIED
    # =====================================================

    async def get_verified(
        self,
        db,
        limit: int = 20,
    ):
        return await self.repo.get_verified(
            db,
            limit,
        )

    # =====================================================
    # STATES
    # =====================================================

    async def get_states(self, db):
        return await self.repo.get_states(db)

    # =====================================================
    # CITIES
    # =====================================================

    async def get_cities(
        self,
        db,
        state: str,
    ):
        return await self.repo.get_cities(
            db,
            state,
        )

    # =====================================================
    # UPDATE DIRECTORY PROFILE
    # =====================================================

    async def update_profile(
        self,
        db,
        school,
        payload,
    ):
        update_data = payload.model_dump(
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(school, field, value)

        return await self.repo.save(
            db,
            school,
        )

    # =====================================================
    # VISIBILITY
    # =====================================================

    async def update_visibility(
        self,
        db,
        school,
        visible: bool,
    ):
        school.is_directory_visible = visible

        # If unpublished, it should not remain featured.
        if not visible:
            school.is_directory_featured = False

        return await self.repo.save(
            db,
            school,
        )

    # =====================================================
    # VERIFY
    # =====================================================

    async def update_verification(
        self,
        db,
        school,
        verified: bool,
    ):
        school.is_directory_verified = verified

        return await self.repo.save(
            db,
            school,
        )

    # =====================================================
    # FEATURE
    # =====================================================

    async def update_featured(
        self,
        db,
        school,
        featured: bool,
    ):
        if featured and not school.is_directory_visible:
            raise ValueError(
                "A school must be visible in the directory before it can be featured."
            )

        school.is_directory_featured = featured

        return await self.repo.save(
            db,
            school,
        )
