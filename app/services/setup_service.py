from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_subject import ClassSubject
from app.models.classes import Class
from app.models.subject import Subject
from app.repositories.setup_repository import AcademicSetupRepository
from app.schemas.academic_setup import (
    AcademicSetupSummaryResponse,
    AcademicTemplateResponse,
    ClassTemplateResponse,
    ConfigureAcademicSetupRequest,
    SubjectTemplateResponse,
)


class AcademicSetupService:
    def __init__(self):
        self.repository = AcademicSetupRepository()

    # ==========================================================
    # GET AVAILABLE TEMPLATES
    # ==========================================================

    async def get_templates(
        self,
        db: AsyncSession,
    ) -> list[AcademicTemplateResponse]:
        templates = await self.repository.get_templates(db)

        response: list[AcademicTemplateResponse] = []

        for template in templates:
            classes: list[ClassTemplateResponse] = []

            sorted_classes = sorted(
                template.class_templates,
                key=lambda c: c.sort_order,
            )

            for class_template in sorted_classes:
                subjects: list[SubjectTemplateResponse] = []

                sorted_subjects = sorted(
                    class_template.subjects,
                    key=lambda x: x.subject_template.name,
                )

                for relation in sorted_subjects:
                    subject = relation.subject_template

                    subjects.append(
                        SubjectTemplateResponse(
                            id=subject.id,
                            name=subject.name,
                            code=subject.code,
                            level=subject.level,
                        )
                    )

                classes.append(
                    ClassTemplateResponse(
                        id=class_template.id,
                        name=class_template.name,
                        level=class_template.level,
                        sort_order=class_template.sort_order,
                        subjects=subjects,
                    )
                )

            response.append(
                AcademicTemplateResponse(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    classes=classes,
                )
            )

        return response

    # ==========================================================
    # CONFIGURE SCHOOL
    # ==========================================================

    async def configure(
        self,
        db: AsyncSession,
        payload: ConfigureAcademicSetupRequest,
        school_id: UUID,
    ) -> AcademicSetupSummaryResponse:
        try:
            # -----------------------------------------
            # Verify template exists
            # -----------------------------------------

            template = await self.repository.get_template(
                db,
                payload.academic_template_id,
            )

            if template is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Academic template not found.",
                )

            # -----------------------------------------
            # Prevent duplicate setup
            # -----------------------------------------

            existing = await self.repository.get_school_classes(
                db,
                school_id,
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Academic setup has already been configured.",
                )

            # -----------------------------------------
            # Validate payload
            # -----------------------------------------

            self._validate_request(
                template,
                payload,
            )

            # -----------------------------------------
            # Build lookup tables
            # -----------------------------------------

            selected_lookup = self._build_selected_lookup(
                payload,
            )

            # -----------------------------------------
            # Clone classes
            # -----------------------------------------

            created_classes = await self._clone_classes(
                db=db,
                school_id=school_id,
                template=template,
                selected_lookup=selected_lookup,
            )

            # -----------------------------------------
            # Clone subjects
            # -----------------------------------------

            created_subjects = await self._clone_subjects(
                db=db,
                school_id=school_id,
                template=template,
                selected_lookup=selected_lookup,
            )

            # -----------------------------------------
            # Create mappings
            # -----------------------------------------

            mappings = await self._build_class_subject_mappings(
                db=db,
                school_id=school_id,
                template=template,
                selected_lookup=selected_lookup,
                class_lookup=created_classes,
                subject_lookup=created_subjects,
            )

            # -----------------------------------------
            # Commit
            # -----------------------------------------

            await db.commit()

            return AcademicSetupSummaryResponse(
                classes_created=len(created_classes),
                subjects_created=len(created_subjects),
                mappings_created=len(mappings),
                message="Academic setup completed successfully.",
            )

        except HTTPException:
            await db.rollback()
            raise

        except Exception:
            await db.rollback()
            raise

    # ==========================================================
    # VALIDATE REQUEST
    # ==========================================================

    def _validate_request(
        self,
        template,
        payload: ConfigureAcademicSetupRequest,
    ) -> None:
        if not payload.classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one class must be selected.",
            )

        template_class_ids = {cls.id for cls in template.class_templates}

        for selected_class in payload.classes:
            if selected_class.template_class_id not in template_class_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid class template: {selected_class.template_class_id}",
                )

        # validate subjects belong to selected class
        class_lookup = {cls.id: cls for cls in template.class_templates}

        for selected_class in payload.classes:
            template_class = class_lookup[selected_class.template_class_id]

            valid_subject_ids = {
                relation.subject_template.id for relation in template_class.subjects
            }

            enabled_subjects = 0

            for subject in selected_class.subjects:
                if subject.template_subject_id not in valid_subject_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "One or more selected subjects "
                            "do not belong to the selected class."
                        ),
                    )

                if subject.enabled:
                    enabled_subjects += 1

            if selected_class.enabled and enabled_subjects == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{template_class.name} must contain at least one subject."
                    ),
                )

    # ==========================================================
    # BUILD LOOKUPS
    # ==========================================================

    def _build_selected_lookup(
        self,
        payload: ConfigureAcademicSetupRequest,
    ):
        lookup = {}

        for school_class in payload.classes:
            subject_lookup = {}

            for subject in school_class.subjects:
                subject_lookup[subject.template_subject_id] = subject.enabled

            lookup[school_class.template_class_id] = {
                "enabled": school_class.enabled,
                "subjects": subject_lookup,
            }

        return lookup

    # ==========================================================
    # CLONE CLASSES
    # ==========================================================

    async def _clone_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        template,
        selected_lookup,
    ):
        school_classes = []

        for template_class in template.class_templates:
            selected = selected_lookup.get(template_class.id)

            if selected is None:
                continue

            if not selected["enabled"]:
                continue

            school_class = Class(
                school_id=school_id,
                template_class_id=template_class.id,
                name=template_class.name,
                level=template_class.level,
                sort_order=template_class.sort_order,
            )

            school_classes.append(school_class)

        await self.repository.create_classes(
            db,
            school_classes,
        )

        return {cls.template_class_id: cls for cls in school_classes}

    # ==========================================================
    # CLONE SUBJECTS
    # ==========================================================

    async def _clone_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        template,
        selected_lookup,
    ):
        subjects = {}

        for template_class in template.class_templates:
            class_selection = selected_lookup.get(template_class.id)

            if class_selection is None:
                continue

            if not class_selection["enabled"]:
                continue

            for relation in template_class.subjects:
                template_subject = relation.subject_template

                enabled = class_selection["subjects"].get(
                    template_subject.id,
                    False,
                )

                if not enabled:
                    continue

                if template_subject.id in subjects:
                    continue

                subjects[template_subject.id] = Subject(
                    school_id=school_id,
                    template_subject_id=template_subject.id,
                    name=template_subject.name,
                    code=template_subject.code,
                )

        await self.repository.create_subjects(
            db,
            list(subjects.values()),
        )

        return subjects

    # ==========================================================
    # CREATE CLASS SUBJECT MAPPINGS
    # ==========================================================

    async def _build_class_subject_mappings(
        self,
        db: AsyncSession,
        school_id: UUID,
        template,
        selected_lookup,
        class_lookup,
        subject_lookup,
    ):
        mappings = []

        for template_class in template.class_templates:
            class_selection = selected_lookup.get(template_class.id)

            if class_selection is None:
                continue

            if not class_selection["enabled"]:
                continue

            school_class = class_lookup[template_class.id]

            for relation in template_class.subjects:
                template_subject = relation.subject_template

                enabled = class_selection["subjects"].get(
                    template_subject.id,
                    False,
                )

                if not enabled:
                    continue

                school_subject = subject_lookup[template_subject.id]

                mappings.append(
                    ClassSubject(
                        school_id=school_id,
                        class_id=school_class.id,
                        subject_id=school_subject.id,
                    )
                )

        await self.repository.create_class_subjects(
            db,
            mappings,
        )

        return mappings
