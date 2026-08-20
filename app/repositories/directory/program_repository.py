from sqlalchemy import select

from app.models.school_program import SchoolProgram


class SchoolProgramRepository:
    async def get_school_programs(
        self,
        db,
        school_id,
    ):
        result = await db.execute(
            select(SchoolProgram)
            .where(SchoolProgram.school_id == school_id)
            .order_by(SchoolProgram.name.asc())
        )

        return result.scalars().all()

    async def get_by_id(
        self,
        db,
        program_id,
    ):
        result = await db.execute(
            select(SchoolProgram).where(SchoolProgram.id == program_id)
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        db,
        program,
    ):
        db.add(program)

        await db.commit()

        await db.refresh(program)

        return program

    async def save(
        self,
        db,
        program,
    ):
        db.add(program)

        await db.commit()

        await db.refresh(program)

        return program

    async def delete(
        self,
        db,
        program,
    ):
        await db.delete(program)

        await db.commit()
