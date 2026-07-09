import asyncio

from app.db.database import async_session_local
from app.db.seeders.academic_templates import seed_academic_templates


async def main():
    async with async_session_local() as db:
        await seed_academic_templates(db)


if __name__ == "__main__":
    asyncio.run(main())
