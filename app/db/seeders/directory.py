import asyncio

from sqlalchemy import update

from app.db.database import async_session_local
from app.models.school import School


async def make_all_schools_directory_featured():
    async with async_session_local() as db:
        try:
            stmt = update(School).values(
                is_directory_visible=True,
                is_directory_verified=True,
                is_directory_featured=True,
            )

            result = await db.execute(stmt)
            await db.commit()

            print(f"Updated {result.rowcount} schools successfully.")

        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(make_all_schools_directory_featured())
