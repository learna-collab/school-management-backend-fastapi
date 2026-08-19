from fastapi import APIRouter

from app.core.deps import DBSession
from app.services.directory_service import DirectorySchoolService

router = APIRouter(
    prefix="/directory/locations",
    tags=["Directory Locations"],
)

service = DirectorySchoolService()


# =====================================================
# STATES
# =====================================================


@router.get("/states")
async def get_states(
    db: DBSession,
):
    return await service.get_states(db)


# =====================================================
# CITIES
# =====================================================


@router.get("/states/{state}/cities")
async def get_cities(
    state: str,
    db: DBSession,
):
    return await service.get_cities(
        db,
        state,
    )
