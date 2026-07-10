from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.school import School
from app.models.user import User, UserRole


class SchoolRepository:
    async def create(self, db, school: School):
        db.add(school)

        await db.commit()

        await db.refresh(school)

        return school

    async def get_all(self, db):
        result = await db.execute(select(School).order_by(School.created_at.desc()))

        return result.scalars().all()

    async def get_by_id(self, db, school_id):
        result = await db.execute(select(School).where(School.id == school_id))

        return result.scalars().first()

    async def get_schools(self, db):
        result = await db.execute(
            select(School)
            .options(selectinload(School.users).selectinload(User.credential))
            .order_by(School.name)
        )

        schools = result.scalars().unique().all()

        response = []

        for school in schools:
            admin = next(
                (user for user in school.users if user.role == UserRole.SCHOOL_ADMIN),
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

        return response

    async def get_by_slug(
        self,
        db,
        slug: str,
    ):
        result = await db.execute(select(School).where(School.slug == slug))

        return result.scalar_one_or_none()

    async def get_by_code(self, db, code):
        result = await db.execute(select(School).where(School.code == code))

        return result.scalars().first()

    async def delete(self, db, school: School):
        await db.delete(school)

        await db.commit()

    async def save(
        self,
        db,
        school: School,
    ):
        db.add(school)

        await db.commit()

        await db.refresh(school)

        return school
