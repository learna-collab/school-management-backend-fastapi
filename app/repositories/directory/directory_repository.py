from sqlalchemy import func, or_, select

from app.models.school import School


class DirectorySchoolRepository:
    async def get_public_schools(
        self,
        db,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        state: str | None = None,
        city: str | None = None,
        school_type: str | None = None,
        ownership_type: str | None = None,
        verified: bool | None = None,
    ):
        conditions = [
            School.is_active.is_(True),
            School.is_directory_visible.is_(True),
        ]

        # ---------------------------------------------
        # SEARCH
        # ---------------------------------------------

        if search:
            search_term = f"%{search.strip()}%"

            conditions.append(
                or_(
                    School.name.ilike(search_term),
                    School.description.ilike(search_term),
                    School.city.ilike(search_term),
                    School.state.ilike(search_term),
                )
            )

        # ---------------------------------------------
        # FILTERS
        # ---------------------------------------------

        if state:
            conditions.append(School.state.ilike(state.strip()))

        if city:
            conditions.append(School.city.ilike(city.strip()))

        if school_type:
            conditions.append(School.school_type == school_type)

        if ownership_type:
            conditions.append(School.ownership_type == ownership_type)

        if verified is not None:
            conditions.append(School.is_directory_verified.is_(verified))

        # ---------------------------------------------
        # TOTAL
        # ---------------------------------------------

        count_stmt = select(func.count(School.id)).where(*conditions)

        count_result = await db.execute(count_stmt)

        total = count_result.scalar_one()

        # ---------------------------------------------
        # DATA
        # ---------------------------------------------

        stmt = (
            select(School)
            .where(*conditions)
            .order_by(
                School.is_directory_verified.desc(),
                School.name.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)

        schools = result.scalars().all()

        return schools, total

    # =====================================================
    # GET PUBLIC SCHOOL BY SLUG
    # =====================================================

    async def get_public_by_slug(
        self,
        db,
        slug: str,
    ):
        stmt = select(School).where(
            School.slug == slug,
            School.is_active.is_(True),
            School.is_directory_visible.is_(True),
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    # =====================================================
    # FEATURED SCHOOLS
    # =====================================================

    async def get_featured(
        self,
        db,
        limit: int = 12,
    ):
        stmt = (
            select(School)
            .where(
                School.is_active.is_(True),
                School.is_directory_visible.is_(True),
                School.is_directory_featured.is_(True),
            )
            .order_by(School.name.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)

        return result.scalars().all()

    # =====================================================
    # VERIFIED SCHOOLS
    # =====================================================

    async def get_verified(
        self,
        db,
        limit: int = 20,
    ):
        stmt = (
            select(School)
            .where(
                School.is_active.is_(True),
                School.is_directory_visible.is_(True),
                School.is_directory_verified.is_(True),
            )
            .order_by(School.name.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)

        return result.scalars().all()

    # =====================================================
    # SCHOOL ADMIN
    # =====================================================

    async def get_by_id(
        self,
        db,
        school_id,
    ):
        stmt = select(School).where(School.id == school_id)

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    # =====================================================
    # STATES
    # =====================================================

    async def get_states(self, db):
        stmt = (
            select(School.state)
            .where(
                School.is_active.is_(True),
                School.is_directory_visible.is_(True),
                School.state.is_not(None),
            )
            .distinct()
            .order_by(School.state.asc())
        )

        result = await db.execute(stmt)

        return [state for state in result.scalars().all() if state]

    # =====================================================
    # CITIES
    # =====================================================

    async def get_cities(
        self,
        db,
        state: str,
    ):
        stmt = (
            select(School.city)
            .where(
                School.is_active.is_(True),
                School.is_directory_visible.is_(True),
                School.state.ilike(state),
                School.city.is_not(None),
            )
            .distinct()
            .order_by(School.city.asc())
        )

        result = await db.execute(stmt)

        return [city for city in result.scalars().all() if city]

    # =====================================================
    # SAVE
    # =====================================================

    async def save(
        self,
        db,
        school: School,
    ):
        db.add(school)

        await db.commit()

        await db.refresh(school)

        return school
