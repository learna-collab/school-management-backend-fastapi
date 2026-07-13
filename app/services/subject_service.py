from app.models.subject import Subject
from app.repositories.subject_repository import (
    subject_repository,
)


class SubjectService:
    def __init__(self):
        self.repo = subject_repository

    async def create_subject(
        self,
        db,
        name,
        school_id,
        code=None,
    ):
        subject = Subject(
            name=name,
            code=code,
            school_id=school_id,
            is_custom=True,
        )

        return await self.repo.create(
            db,
            subject,
        )

    async def get_school_subjects(
        self,
        db,
        school_id,
    ):
        subjects = await self.repo.get_school_subjects(
            db,
            school_id,
        )

        return {
            "subjects": [
                {
                    "id": str(subject.id),
                    "name": subject.name,
                    "code": subject.code,
                }
                for subject in subjects
            ]
        }

    # ==================================================
    # CLASS SUBJECTS
    # ==================================================

    async def assign_subject_to_class(
        self,
        db,
        class_id,
        subject_id,
        school_id,
    ):
        subject = await self.repo.get_by_id(
            db,
            subject_id,
        )

        if not subject:
            return {
                "success": False,
                "message": "Subject not found",
            }

        if subject.school_id != school_id:
            return {
                "success": False,
                "message": "Subject does not belong to this school",
            }

        existing = await self.repo.subject_assigned_to_class(
            db=db,
            class_id=class_id,
            subject_id=subject_id,
        )

        if existing:
            return {
                "success": False,
                "message": "Subject already assigned to class",
            }

        assignment = await self.repo.assign_subject_to_class(
            db=db,
            class_id=class_id,
            subject_id=subject_id,
        )

        return {
            "success": True,
            "message": "Subject assigned successfully",
            "assignment_id": str(assignment.id),
        }

    async def get_class_subjects(
        self,
        db,
        class_id,
        school_id,
    ):
        subjects = await self.repo.get_class_subjects(
            db=db,
            class_id=class_id,
            school_id=school_id,
        )

        return {
            "subjects": [
                {
                    "id": str(subject.id),
                    "name": subject.name,
                    "code": subject.code,
                }
                for subject in subjects
            ]
        }

    async def remove_subject_from_class(
        self,
        db,
        class_id,
        subject_id,
    ):
        deleted = await self.repo.remove_subject_from_class(
            db=db,
            class_id=class_id,
            subject_id=subject_id,
        )

        return {
            "success": deleted,
        }


subject_service = SubjectService()
