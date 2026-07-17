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
    AssignSubjectsRequest,
    ClassTemplateResponse,
    ConfigureAcademicSetupRequest,
    CreateClassRequest,
    CreateSubjectRequest,
    SchoolAcademicSetupResponse,
    SchoolClassResponse,
    SchoolSubjectResponse,
    SubjectTemplateResponse,
    UpdateClassRequest,
    UpdateSubjectRequest,
)


class AcademicSetupService:
    """
    Academic Setup Service.

    Responsible for:

    • Loading academic templates
    • Configuring a school's academic structure
    • Returning configured setup
    • Managing classes
    • Managing subjects
    • Managing class-subject mappings
    """

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
                key=lambda c: (
                    c.level,
                    c.sort_order,
                    c.name,
                ),
            )

            for class_template in sorted_classes:
                subjects: list[SubjectTemplateResponse] = []

                sorted_subjects = sorted(
                    class_template.subjects,
                    key=lambda relation: (relation.subject_template.name,),
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
    # GET SCHOOL SETUP
    # ==========================================================

    async def get_school_setup(
        self,
        db: AsyncSession,
        school_id: UUID,
    ) -> SchoolAcademicSetupResponse:
        school_classes = await self.repository.get_school_classes(
            db,
            school_id,
        )

        if not school_classes:
            return SchoolAcademicSetupResponse(
                configured=False,
                classes=[],
            )

        response_classes: list[SchoolClassResponse] = []

        for school_class in school_classes:
            subjects: list[SchoolSubjectResponse] = []

            sorted_mappings = sorted(
                school_class.class_subjects,
                key=lambda mapping: mapping.subject.name,
            )

            for mapping in sorted_mappings:
                subject = mapping.subject

                subjects.append(
                    SchoolSubjectResponse(
                        id=subject.id,
                        name=subject.name,
                        code=subject.code,
                        is_custom=subject.is_custom,
                    )
                )

            response_classes.append(
                SchoolClassResponse(
                    id=school_class.id,
                    name=school_class.name,
                    level=school_class.level,
                    sort_order=school_class.sort_order,
                    is_custom=school_class.is_custom,
                    subjects=subjects,
                )
            )

        response_classes.sort(
            key=lambda cls: (
                cls.level.value if hasattr(cls.level, "value") else str(cls.level),
                cls.sort_order,
                cls.name,
            )
        )

        return SchoolAcademicSetupResponse(
            configured=True,
            classes=response_classes,
        )

    # ==========================================================
    # CONFIGURE SCHOOL
    # ==========================================================

    async def configure(
        self,
        db: AsyncSession,
        payload: ConfigureAcademicSetupRequest,
        school_id: UUID,
        allow_existing: bool = False,
    ) -> AcademicSetupSummaryResponse:
        try:
            # --------------------------------------------------
            # Load academic template
            # --------------------------------------------------

            template = await self.repository.get_template(
                db,
                payload.academic_template_id,
            )

            if template is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Academic template not found.",
                )

            # --------------------------------------------------
            # Prevent configuring twice
            # --------------------------------------------------

            existing = await self.repository.get_school_classes(
                db,
                school_id,
            )

            if existing and not allow_existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Academic setup has already been configured.",
                )

            # --------------------------------------------------
            # Validate incoming payload
            # --------------------------------------------------

            self._validate_request(
                template,
                payload,
            )

            # --------------------------------------------------
            # Build lookup dictionaries
            # --------------------------------------------------

            selected_lookup = self._build_selected_lookup(
                payload,
            )
            # -----------------------------------------
            # Build lookup tables
            # -----------------------------------------

            selected_lookup = self._build_selected_lookup(
                payload,
            )

            # -----------------------------------------
            # Clone template classes
            # -----------------------------------------

            created_classes = await self._clone_classes(
                db=db,
                school_id=school_id,
                template=template,
                selected_lookup=selected_lookup,
            )

            # -----------------------------------------
            # Clone template subjects
            # -----------------------------------------

            created_subjects = await self._clone_subjects(
                db=db,
                school_id=school_id,
                template=template,
                selected_lookup=selected_lookup,
            )

            # -----------------------------------------
            # Create template class-subject mappings
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
            # Create custom classes
            # -----------------------------------------

            custom_classes = await self._create_custom_classes(
                db=db,
                school_id=school_id,
                payload=payload,
            )

            # -----------------------------------------
            # Create custom subjects
            # -----------------------------------------

            custom_subjects = await self._create_custom_subjects(
                db=db,
                school_id=school_id,
                payload=payload,
                class_lookup=created_classes,
                custom_classes=custom_classes,
            )

            # -----------------------------------------
            # Commit transaction
            # -----------------------------------------

            await db.commit()
            setup = await self.get_school_setup(
                db=db,
                school_id=school_id,
            )

            return AcademicSetupSummaryResponse(
                setup=setup,
                classes_created=len(created_classes) + len(custom_classes),
                subjects_created=len(created_subjects) + len(custom_subjects),
                mappings_created=len(mappings),
                message="Academic setup completed successfully.",
            )
        except HTTPException:
            await db.rollback()
            raise

        except Exception as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

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

        template_lookup = {cls.id: cls for cls in template.class_templates}

        class_names: set[str] = set()

        for school_class in payload.classes:
            # ----------------------------------------
            # Duplicate class names
            # ----------------------------------------

            class_name = school_class.name.strip().lower()

            if class_name in class_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate class '{school_class.name}'.",
                )

            class_names.add(class_name)

            # ----------------------------------------
            # Template class validation
            # ----------------------------------------

            if school_class.template_class_id:
                if school_class.template_class_id not in template_lookup:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid template class selected.",
                    )

                template_class = template_lookup[school_class.template_class_id]

                valid_subjects = {
                    relation.subject_template.id for relation in template_class.subjects
                }

                subject_names: set[str] = set()

                enabled_subjects = 0

                for subject in school_class.subjects:
                    if (
                        subject.template_subject_id
                        and subject.template_subject_id not in valid_subjects
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                "One or more selected subjects do not "
                                "belong to the selected class."
                            ),
                        )

                    subject_name = subject.name.strip().lower()

                    if subject_name in subject_names:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Duplicate subject '{subject.name}' "
                                f"in {school_class.name}."
                            ),
                        )

                    subject_names.add(subject_name)

                    if subject.enabled:
                        enabled_subjects += 1

                if school_class.enabled and enabled_subjects == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"{school_class.name} must contain at least one subject."
                        ),
                    )

            # ----------------------------------------
            # Custom class validation
            # ----------------------------------------

            else:
                if not school_class.subjects:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"{school_class.name} must contain at least one subject."
                        ),
                    )

                subject_names: set[str] = set()

                enabled_subjects = 0

                for subject in school_class.subjects:
                    subject_name = subject.name.strip().lower()

                    if subject_name in subject_names:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Duplicate subject '{subject.name}' "
                                f"in {school_class.name}."
                            ),
                        )

                    subject_names.add(subject_name)

                    if subject.enabled:
                        enabled_subjects += 1

                if enabled_subjects == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"{school_class.name} must contain "
                            "at least one enabled subject."
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
            if school_class.template_class_id is None:
                continue

            subject_lookup = {}

            for subject in school_class.subjects:
                if subject.template_subject_id is None:
                    continue

                subject_lookup[subject.template_subject_id] = {
                    "enabled": subject.enabled,
                    "name": subject.name,
                }

            lookup[school_class.template_class_id] = {
                "enabled": school_class.enabled,
                "name": school_class.name,
                "level": school_class.level,
                "subjects": subject_lookup,
            }

        return lookup

    # ==========================================================
    # CLONE TEMPLATE CLASSES
    # ==========================================================

    async def _clone_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        template,
        selected_lookup,
    ):
        school_classes: list[Class] = []

        for template_class in template.class_templates:
            selected = selected_lookup.get(
                template_class.id,
            )

            if selected is None:
                continue

            if not selected["enabled"]:
                continue

            school_class = Class(
                school_id=school_id,
                template_class_id=template_class.id,
                name=selected["name"],
                level=selected["level"],
                sort_order=template_class.sort_order,
                is_custom=False,
            )

            school_classes.append(
                school_class,
            )

        await self.repository.bulk_create_classes(
            db,
            school_classes,
        )

        return {cls.template_class_id: cls for cls in school_classes}

    # ==========================================================
    # CLONE TEMPLATE SUBJECTS
    # ==========================================================

    async def _clone_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        template,
        selected_lookup,
    ):
        subjects: dict[UUID, Subject] = {}

        for template_class in template.class_templates:
            class_selection = selected_lookup.get(
                template_class.id,
            )

            if class_selection is None:
                continue

            if not class_selection["enabled"]:
                continue

            for relation in template_class.subjects:
                template_subject = relation.subject_template

                subject_selection = class_selection["subjects"].get(
                    template_subject.id,
                )

                if subject_selection is None:
                    continue

                if not subject_selection["enabled"]:
                    continue

                # -----------------------------------------
                # Prevent duplicate subjects across classes
                # -----------------------------------------

                if template_subject.id in subjects:
                    continue

                subjects[template_subject.id] = Subject(
                    school_id=school_id,
                    template_subject_id=template_subject.id,
                    name=subject_selection["name"],
                    code=template_subject.code,
                    is_custom=False,
                )

        await self.repository.bulk_create_subjects(
            db,
            list(subjects.values()),
        )

        return subjects

    # ==========================================================
    # CREATE TEMPLATE CLASS-SUBJECT MAPPINGS
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
        mappings: list[ClassSubject] = []

        for template_class in template.class_templates:
            class_selection = selected_lookup.get(
                template_class.id,
            )

            if class_selection is None:
                continue

            if not class_selection["enabled"]:
                continue

            school_class = class_lookup[template_class.id]

            for relation in template_class.subjects:
                template_subject = relation.subject_template

                subject_selection = class_selection["subjects"].get(
                    template_subject.id,
                )

                if subject_selection is None:
                    continue

                if not subject_selection["enabled"]:
                    continue

                school_subject = subject_lookup[template_subject.id]

                mappings.append(
                    ClassSubject(
                        school_id=school_id,
                        class_id=school_class.id,
                        subject_id=school_subject.id,
                    )
                )

        await self.repository.bulk_create_mappings(
            db,
            mappings,
        )

        return mappings

    # ==========================================================
    # CREATE CUSTOM CLASSES
    # ==========================================================

    async def _create_custom_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: ConfigureAcademicSetupRequest,
    ) -> dict[str, Class]:
        custom_classes: list[Class] = []

        for school_class in payload.classes:
            # Skip template classes
            if school_class.template_class_id is not None:
                continue

            if not school_class.enabled:
                continue

            custom_classes.append(
                Class(
                    school_id=school_id,
                    template_class_id=None,
                    name=school_class.name,
                    level=school_class.level,
                    sort_order=school_class.sort_order,
                    is_custom=True,
                )
            )

        if custom_classes:
            await self.repository.bulk_create_classes(
                db,
                custom_classes,
            )

        return {cls.name.lower(): cls for cls in custom_classes}

    # ==========================================================
    # CREATE CUSTOM SUBJECTS
    # ==========================================================

    async def _create_custom_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: ConfigureAcademicSetupRequest,
        class_lookup: dict,
        custom_classes: dict,
    ) -> dict[str, Subject]:
        created_subjects: dict[str, Subject] = {}
        mappings: list[ClassSubject] = []

        for school_class in payload.classes:
            if not school_class.enabled:
                continue

            # -----------------------------------------
            # Resolve school class
            # -----------------------------------------

            if school_class.template_class_id:
                school_db_class = class_lookup.get(
                    school_class.template_class_id,
                )

            else:
                school_db_class = custom_classes.get(
                    school_class.name.lower(),
                )

            if school_db_class is None:
                continue

            # -----------------------------------------
            # Process custom subjects
            # -----------------------------------------

            for subject in school_class.subjects:
                if not subject.enabled:
                    continue

                # Skip template subjects.
                # They were already created in _clone_subjects()
                if subject.template_subject_id:
                    continue

                key = subject.name.strip().lower()

                school_subject = created_subjects.get(key)

                if school_subject is None:
                    school_subject = Subject(
                        school_id=school_id,
                        template_subject_id=None,
                        name=subject.name,
                        code=subject.code,
                        is_custom=True,
                    )

                    db.add(school_subject)

                    await db.flush()

                    created_subjects[key] = school_subject
                # -----------------------------------------
                # Create Class-Subject mapping
                # -----------------------------------------

                mappings.append(
                    ClassSubject(
                        school_id=school_id,
                        class_id=school_db_class.id,
                        subject_id=school_subject.id,
                    )
                )

        # -----------------------------------------
        # Save mappings
        # -----------------------------------------

        if mappings:
            await self.repository.bulk_create_mappings(
                db,
                mappings,
            )

        return created_subjects

    # ==========================================================
    # CLASS CRUD
    # ==========================================================

    async def create_class(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: CreateClassRequest,
    ):
        try:
            school_class = Class(
                school_id=school_id,
                name=payload.name,
                level=payload.level,
                sort_order=payload.sort_order,
                template_class_id=None,
                is_custom=True,
            )

            result = await self.repository.create_class(
                db,
                school_class,
            )

            await db.commit()

            return result

        except Exception as exc:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail=str(exc),
            )

    async def update_class(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        payload: UpdateClassRequest,
    ):
        school_class = await self.repository.get_class(
            db,
            class_id,
        )

        if not school_class:
            raise HTTPException(
                status_code=404,
                detail="Class not found.",
            )

        if school_class.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot update this class.",
            )

        if payload.name is not None:
            school_class.name = payload.name

        if payload.level is not None:
            school_class.level = payload.level

        if payload.sort_order is not None:
            school_class.sort_order = payload.sort_order

        result = await self.repository.update_class(
            db,
            school_class,
        )

        await db.commit()

        return result

    async def delete_class(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
    ):
        school_class = await self.repository.get_class(
            db,
            class_id,
        )

        if not school_class:
            raise HTTPException(
                status_code=404,
                detail="Class not found.",
            )

        if school_class.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot delete this class.",
            )

        await self.repository.remove_class_subjects(
            db,
            class_id,
        )

        await self.repository.delete_class(
            db,
            school_class,
        )

        await db.commit()

        return {"message": "Class deleted successfully."}

    # ==========================================================
    # SUBJECT CRUD
    # ==========================================================

    async def create_subject(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: CreateSubjectRequest,
    ):
        subject = Subject(
            school_id=school_id,
            name=payload.name,
            code=payload.code,
            template_subject_id=None,
            is_custom=True,
        )

        result = await self.repository.create_subject(
            db,
            subject,
        )

        await db.commit()

        return result

    async def update_subject(
        self,
        db: AsyncSession,
        school_id: UUID,
        subject_id: UUID,
        payload: UpdateSubjectRequest,
    ):
        subject = await self.repository.get_subject(
            db,
            subject_id,
        )

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found.",
            )

        if subject.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot update this subject.",
            )

        if payload.name is not None:
            subject.name = payload.name

        if payload.code is not None:
            subject.code = payload.code

        result = await self.repository.update_subject(
            db,
            subject,
        )

        await db.commit()

        return result

    async def delete_subject(
        self,
        db: AsyncSession,
        school_id: UUID,
        subject_id: UUID,
    ):
        subject = await self.repository.get_subject(
            db,
            subject_id,
        )

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found.",
            )

        if subject.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot delete this subject.",
            )

        await self.repository.remove_subject_mappings(
            db,
            subject_id,
        )

        await self.repository.delete_subject(
            db,
            subject,
        )

        await db.commit()

        return {"message": "Subject deleted successfully."}

    # ==========================================================
    # ASSIGN SUBJECTS TO CLASS
    # ==========================================================

    async def assign_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        payload: AssignSubjectsRequest,
    ):
        school_class = await self.repository.get_class(
            db,
            class_id,
        )

        if not school_class:
            raise HTTPException(
                status_code=404,
                detail="Class not found.",
            )

        if school_class.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="Invalid class.",
            )

        await self.repository.remove_class_subjects(
            db,
            class_id,
        )

        mappings = []

        for subject_id in payload.subject_ids:
            subject = await self.repository.get_subject(
                db,
                subject_id,
            )

            if not subject:
                raise HTTPException(
                    status_code=404,
                    detail=f"Subject {subject_id} not found.",
                )

            if subject.school_id != school_id:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid subject.",
                )

            mappings.append(
                ClassSubject(
                    school_id=school_id,
                    class_id=class_id,
                    subject_id=subject_id,
                )
            )

        await self.repository.bulk_create_mappings(
            db,
            mappings,
        )

        await db.commit()

        return {
            "message": "Subjects assigned successfully.",
            "count": len(mappings),
        }

    # ==========================================================
    # UPDATE SCHOOL SETUP
    # ==========================================================

    async def update_setup(
        self,
        db: AsyncSession,
        payload: ConfigureAcademicSetupRequest,
        school_id: UUID,
    ):
        """
        Rebuild the school's academic structure from scratch.

        The frontend sends the complete structure every time Save is clicked,
        so we simply clear the existing setup and recreate it.
        """
        try:
            await self.repository.clear_school_setup(
                db,
                school_id,
            )

            await db.flush()

            return await self.configure(
                db=db,
                payload=payload,
                school_id=school_id,
                allow_existing=True,
            )

        except HTTPException:
            await db.rollback()
            raise

        except Exception as exc:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail=str(exc),
            )


academic_setup_service = AcademicSetupService()
