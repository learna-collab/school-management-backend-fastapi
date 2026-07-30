from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DBSession, RequireSuperAdmin
from app.schemas.super_admin_academic import (
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    TermCreate,
    TermResponse,
    TermUpdate,
)
from app.services.super_admin_academic_service import (
    SuperAdminAcademicService,
)

router = APIRouter(
    prefix="/super-admin/academic",
    tags=["Super Admin Academic"],
)

service = SuperAdminAcademicService()


# ======================================================
# Sessions
# ======================================================


@router.post(
    "/sessions",
    response_model=SessionResponse,
)
async def create_session(
    payload: SessionCreate,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.create_session(
        db,
        payload.name,
        payload.start_date,
        payload.end_date,
    )


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
)
async def list_sessions(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.list_sessions(db)


@router.put(
    "/sessions/{session_id}",
    response_model=SessionResponse,
)
async def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.update_session(
        db,
        session_id,
        payload.name,
        payload.start_date,
        payload.end_date,
    )


@router.patch(
    "/sessions/{session_id}/activate",
    response_model=SessionResponse,
)
async def activate_session(
    session_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.set_session_active(db, session_id, True)


@router.patch(
    "/sessions/{session_id}/deactivate",
    response_model=SessionResponse,
)
async def deactivate_session(
    session_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.set_session_active(db, session_id, False)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    await service.delete_session(db, session_id)
    return {"message": "Session deleted successfully"}


# ======================================================
# Terms
# ======================================================


@router.post(
    "/terms",
    response_model=TermResponse,
)
async def create_term(
    payload: TermCreate,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.create_term(
        db,
        payload.name,
        payload.sort_order,
    )


@router.get(
    "/terms",
    response_model=list[TermResponse],
)
async def list_terms(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.list_terms(db)


@router.put(
    "/terms/{term_id}",
    response_model=TermResponse,
)
async def update_term(
    term_id: UUID,
    payload: TermUpdate,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.update_term(
        db,
        term_id,
        payload.name,
        payload.sort_order,
    )


@router.patch(
    "/terms/{term_id}/activate",
    response_model=TermResponse,
)
async def activate_term(
    term_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.set_term_active(db, term_id, True)


@router.patch(
    "/terms/{term_id}/deactivate",
    response_model=TermResponse,
)
async def deactivate_term(
    term_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.set_term_active(db, term_id, False)


@router.delete("/terms/{term_id}")
async def delete_term(
    term_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    await service.delete_term(db, term_id)
    return {"message": "Term deleted successfully"}
