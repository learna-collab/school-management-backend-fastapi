from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.school import School
from app.models.user import User, UserRole


class SchoolRepository:
    # =====================================================
    # CREATE
    # =====================================================

    async def create(self, db, school: School):
        """
        Add a school to the current transaction.
        Does not commit.
        """
        db.add(school)
        await db.flush()
        await db.refresh(school)
        return school

    # =====================================================
    # GET ALL
    # =====================================================

    async def get_all(self, db):
        result = await db.execute(select(School).order_by(School.created_at.desc()))
        return result.scalars().all()

    # =====================================================
    # GET BY ID
    # =====================================================

    async def get_by_id(self, db, school_id):
        result = await db.execute(
            select(School)
            .options(selectinload(School.users).selectinload(User.credential))
            .where(School.id == school_id)
        )
        return result.scalar_one_or_none()

    # =====================================================
    # GET SCHOOLS
    # =====================================================

    async def get_schools(
        self,
        db,
        search: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ):
        query = (
            select(School)
            .options(selectinload(School.users).selectinload(User.credential))
            .order_by(School.name)
        )

        if search:
            query = query.where(
                or_(
                    School.name.ilike(f"%{search}%"),
                    School.slug.ilike(f"%{search}%"),
                    School.email.ilike(f"%{search}%"),
                    School.phone.ilike(f"%{search}%"),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = query.offset((page - 1) * per_page).limit(per_page)

        schools = (await db.execute(query)).scalars().unique().all()

        response = []

        for school in schools:
            admin = next(
                (u for u in school.users if u.role == UserRole.SCHOOL_ADMIN),
                None,
            )

            credential = admin.credential if admin else None

            response.append(
                {
                    "id": str(school.id),
                    "name": school.name,
                    "slug": school.slug,
                    "email": school.email,
                    "phone": school.phone,
                    "state": school.state,
                    "website": school.website,
                    "address": school.address,
                    "description": school.description,
                    "whatsapp_number": school.whatsapp_number,
                    "subscription_plan": school.subscription_plan,
                    "is_active": school.is_active,
                    "admin": {
                        "id": str(admin.id) if admin else None,
                        "first_name": admin.first_name if admin else None,
                        "last_name": admin.last_name if admin else None,
                        "email": admin.email if admin else None,
                        "username": credential.username if credential else None,
                        "password": credential.password if credential else None,
                    },
                }
            )

        return {
            "items": response,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    # =====================================================
    # GET BY SLUG
    # =====================================================

    async def get_by_slug(self, db, slug: str):
        result = await db.execute(select(School).where(School.slug == slug))
        return result.scalar_one_or_none()

    # =====================================================
    # GET BY CODE
    # =====================================================

    async def get_by_code(self, db, code):
        result = await db.execute(select(School).where(School.code == code))
        return result.scalar_one_or_none()

    # =====================================================
    # SLUG EXISTS
    # =====================================================

    async def slug_exists(self, db, slug: str) -> bool:
        result = await db.execute(select(School.id).where(School.slug == slug))
        return result.scalar_one_or_none() is not None

    # =====================================================
    # COUNT SCHOOLS
    # =====================================================

    async def count(self, db):
        result = await db.execute(select(func.count()).select_from(School))
        return result.scalar_one()

    # =====================================================
    # UPDATE
    # =====================================================

    async def update(self, db, school: School, payload):
        """
        Updates an existing school inside the current transaction.
        Does not commit.
        """

        school.name = payload.school_name
        school.phone = payload.phone
        school.website = payload.website or None
        school.whatsapp_number = payload.whatsapp_number or None
        school.state = payload.state
        school.address = payload.address
        school.description = payload.description or None
        school.email = payload.admin_email

        db.add(school)

        await db.flush()
        school = await self.get_by_id(db, school.id)

        return school

    # =====================================================
    # DELETE
    # =====================================================

    async def delete(self, db, school: School):
        """
        Deletes inside the current transaction.
        """
        await db.delete(school)
        await db.flush()

    # =====================================================
    # SAVE
    # =====================================================

    async def save(self, db, school: School):
        """
        Saves changes without committing.
        """
        db.add(school)
        await db.flush()
        await db.refresh(school)
        return school
