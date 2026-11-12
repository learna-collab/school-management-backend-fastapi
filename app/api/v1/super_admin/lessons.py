from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.core.deps import DBSession, RequireSuperAdmin
from app.schemas.learning_centre import LessonLearningDocument
from app.schemas.lesson import (
    LessonResponse,
    SimpleClassResponse,
    SimpleSessionResponse,
    SimpleSubjectResponse,
    SimpleTermResponse,
)
from app.services.learning_content_service import (
    LearningContentService,
)
from app.services.lesson_service import LessonService

router = APIRouter(
    prefix="/super-admin/lessons",
    tags=["Super Admin Lessons"],
)


service = LessonService()
learning_content_service = LearningContentService()


# ==========================================================
# LEARNING CONTENT SERIALIZATION
# ==========================================================


def serialize_learning_content(content):
    """
    Convert a LessonLearningContent ORM instance into
    a JSON-serializable dictionary.

    This avoids introducing another response schema.
    """

    return {
        "id": content.id,
        "lesson_id": content.lesson_id,
        "school_id": content.school_id,
        "version": content.version,
        "status": content.status,
        "content": content.content,
        "generation_notes": content.generation_notes,
        "review_notes": content.review_notes,
        "generated_by": content.generated_by,
        "reviewed_by": content.reviewed_by,
        "published_by": content.published_by,
        "published_at": content.published_at,
    }


# ==========================================================
# EXISTING LESSON ENDPOINTS
# ==========================================================


@router.get(
    "/classes",
    response_model=list[SimpleClassResponse],
)
async def get_classes(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_classes(db)


@router.get(
    "/subjects",
    response_model=list[SimpleSubjectResponse],
)
async def get_subjects(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_subjects(db)


@router.get(
    "/sessions",
    response_model=list[SimpleSessionResponse],
)
async def get_sessions(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_sessions(db)


@router.get(
    "/terms",
    response_model=list[SimpleTermResponse],
)
async def get_terms(
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_terms(db)


@router.post(
    "/upload",
    response_model=LessonResponse,
)
async def upload_lesson(
    db: DBSession,
    current_user: RequireSuperAdmin,
    class_template_id: Annotated[UUID, Form(...)],
    subject_template_id: Annotated[UUID, Form(...)],
    session_id: Annotated[UUID, Form(...)],
    term_id: Annotated[UUID, Form(...)],
    week_number: Annotated[int, Form(...)],
    file: Annotated[UploadFile, File(...)],
):
    return await service.upload_lesson(
        db=db,
        created_by=current_user.id,
        class_template_id=class_template_id,
        subject_template_id=subject_template_id,
        session_id=session_id,
        term_id=term_id,
        week_number=week_number,
        file=file,
    )


@router.get(
    "",
    response_model=list[LessonResponse],
)
async def list_lessons(
    db: DBSession,
    _: RequireSuperAdmin,
    class_template_id: Annotated[UUID, Query(...)],
    session_id: Annotated[UUID, Query(...)],
    term_id: Annotated[UUID, Query(...)],
    week_number: Annotated[int | None, Query()] = None,
):
    return await service.get_lessons(
        db=db,
        class_template_id=class_template_id,
        session_id=session_id,
        term_id=term_id,
        week_number=week_number,
    )


# ==========================================================
# AI LEARNING CONTENT GENERATION
# ==========================================================


@router.post(
    "/{lesson_id}/learning-content/generate",
)
async def generate_learning_content(
    lesson_id: UUID,
    db: DBSession,
    current_user: RequireSuperAdmin,
):
    content = await learning_content_service.generate_for_lesson(
        db=db,
        lesson_id=lesson_id,
        generated_by=current_user.id,
    )

    return serialize_learning_content(content)


# ==========================================================
# GET ALL CONTENT VERSIONS FOR A LESSON
# ==========================================================


@router.get(
    "/{lesson_id}/learning-content",
)
async def get_lesson_learning_versions(
    lesson_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    versions = await learning_content_service.get_lesson_versions(
        db=db,
        lesson_id=lesson_id,
    )

    return [serialize_learning_content(content) for content in versions]


# ==========================================================
# GET ONE LEARNING CONTENT VERSION
# ==========================================================


@router.get(
    "/learning-content/{content_id}",
)
async def get_learning_content(
    content_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    content = await learning_content_service.get_content(
        db=db,
        content_id=content_id,
    )

    return serialize_learning_content(content)


# ==========================================================
# REVIEW / EDIT GENERATED CONTENT
# ==========================================================


@router.patch(
    "/learning-content/{content_id}/review",
)
async def review_learning_content(
    content_id: UUID,
    content_data: LessonLearningDocument,
    db: DBSession,
    current_user: RequireSuperAdmin,
    review_notes: Annotated[str | None, Query()] = None,
):
    content = await learning_content_service.review_content(
        db=db,
        content_id=content_id,
        reviewed_by=current_user.id,
        content_data=content_data,
        review_notes=review_notes,
    )

    return serialize_learning_content(content)


# ==========================================================
# PUBLISH REVIEWED CONTENT
# ==========================================================


@router.post(
    "/learning-content/{content_id}/publish",
)
async def publish_learning_content(
    content_id: UUID,
    db: DBSession,
    current_user: RequireSuperAdmin,
):
    content = await learning_content_service.publish_content(
        db=db,
        content_id=content_id,
        published_by=current_user.id,
    )

    return serialize_learning_content(content)


# ==========================================================
# EXISTING LESSON RETRIEVAL / DELETION
# ==========================================================


@router.get(
    "/{lesson_id}",
    response_model=LessonResponse,
)
async def get_lesson(
    lesson_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_lesson(db, lesson_id)


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    await service.delete(db, lesson_id)

    return {"message": "Lesson deleted successfully"}


@router.get(
    "/classes/{class_template_id}/subjects",
    response_model=list[SimpleSubjectResponse],
)
async def get_class_subjects(
    class_template_id: UUID,
    db: DBSession,
    _: RequireSuperAdmin,
):
    return await service.get_class_subjects(
        db,
        class_template_id,
    )
