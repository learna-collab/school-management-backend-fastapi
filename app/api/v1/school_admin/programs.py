from fastapi import APIRouter, HTTPException, status

from app.core.deps import DBSession, RequireSchoolAdmin
from app.schemas.directory.program import (
    SchoolProgramCreate,
    SchoolProgramUpdate,
)
from app.services.directory.program_service import (
    SchoolProgramService,
)

router = APIRouter(
    prefix="/school-admin/directory/programs",
    tags=["School Admin Programs"],
)

service = SchoolProgramService()


@router.get("")
async def list_programs(
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.get_programs(
        db,
        current_user.school_id,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_program(
    payload: SchoolProgramCreate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    return await service.create_program(
        db,
        current_user.school_id,
        payload,
    )


@router.put("/{program_id}")
async def update_program(
    program_id,
    payload: SchoolProgramUpdate,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    program = await service.repo.get_by_id(
        db,
        program_id,
    )

    if not program or program.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    return await service.update_program(
        db,
        program,
        payload,
    )


@router.delete("/{program_id}")
async def delete_program(
    program_id,
    db: DBSession,
    current_user: RequireSchoolAdmin,
):
    program = await service.repo.get_by_id(
        db,
        program_id,
    )

    if not program or program.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    await service.delete_program(
        db,
        program,
    )

    return {
        "message": "Program deleted successfully",
    }
