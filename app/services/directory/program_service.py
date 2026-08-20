from app.models.school_program import SchoolProgram
from app.repositories.directory.program_repository import (
    SchoolProgramRepository,
)


class SchoolProgramService:
    def __init__(self):
        self.repo = SchoolProgramRepository()

    async def get_programs(
        self,
        db,
        school_id,
    ):
        return await self.repo.get_school_programs(
            db,
            school_id,
        )

    async def create_program(
        self,
        db,
        school_id,
        payload,
    ):
        program = SchoolProgram(
            school_id=school_id,
            name=payload.name,
            description=payload.description,
            is_available=payload.is_available,
        )

        return await self.repo.create(
            db,
            program,
        )

    async def update_program(
        self,
        db,
        program,
        payload,
    ):
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(
                program,
                field,
                value,
            )

        return await self.repo.save(
            db,
            program,
        )

    async def delete_program(
        self,
        db,
        program,
    ):
        await self.repo.delete(
            db,
            program,
        )
