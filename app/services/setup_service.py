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
    • Updating an existing academic structure
    • Returning configured setup
    • Managing classes
    • Managing subjects
    • Managing class-subject mappings

    IMPORTANT:

    Reconfiguration NEVER deletes existing Class or Subject records.

    Classes and subjects may already be referenced by:
    • student enrollments
    • result records
    • attendance
    • lessons
    • other historical/operational records

    Therefore update_setup() only synchronizes the current
    ClassSubject mappings and reuses existing classes/subjects.
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

        # ClassTemplate rows are globally unique by:
        # (name, level)
        #
        # Therefore we cannot rely on:
        # template.class_templates
        #
        # Instead, load all unique class templates and match them
        # against the levels supported by each AcademicTemplate.
        all_classes = await self.repository.get_all_template_classes(db)

        response: list[AcademicTemplateResponse] = []

        for template in templates:
            classes: list[ClassTemplateResponse] = []

            template_levels = set(template.levels)

            matching_classes = [
                class_template
                for class_template in all_classes
                if class_template.level in template_levels
            ]

            sorted_classes = sorted(
                matching_classes,
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
        """
        Return the school's CURRENT academic configuration.

        IMPORTANT:

        Classes and subjects are preserved in the database even after
        a reset or reconfiguration because they may be referenced by
        historical/operational records.

        Therefore, a class is considered part of the current academic
        setup only when it has at least one current ClassSubject mapping.
        """

        school_classes = await self.repository.get_school_classes_with_mappings(
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
            # IMPORTANT:
            #
            # ClassTemplate rows are globally unique by:
            # (name, level)
            #
            # An AcademicTemplate can contain multiple levels.
            #
            # Example:
            #
            # Nursery, Primary & Secondary
            #     -> NURSERY
            #     -> PRIMARY
            #     -> SECONDARY
            #
            # Therefore resolve classes by the template's levels,
            # not through template.class_templates.
            # --------------------------------------------------

            template_classes = await self.repository.get_template_classes(
                db=db,
                levels=template.levels,
            )

            # --------------------------------------------------
            # Prevent configuring twice
            #
            # Historical classes may still exist after a reset.
            # Only current ClassSubject mappings determine whether
            # the academic setup is currently configured.
            # --------------------------------------------------

            existing = await self.repository.get_school_classes_with_mappings(
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
                template_classes,
                payload,
            )

            # --------------------------------------------------
            # Build lookup
            # --------------------------------------------------

            selected_lookup = self._build_selected_lookup(
                payload=payload,
            )

            # --------------------------------------------------
            # Create/reuse template classes
            # --------------------------------------------------

            created_classes = await self._clone_classes(
                db=db,
                school_id=school_id,
                template_classes=template_classes,
                selected_lookup=selected_lookup,
            )

            # --------------------------------------------------
            # Create/reuse template subjects
            # --------------------------------------------------

            created_subjects = await self._clone_subjects(
                db=db,
                school_id=school_id,
                template_classes=template_classes,
                selected_lookup=selected_lookup,
            )

            # --------------------------------------------------
            # Create template mappings
            # --------------------------------------------------

            mappings = await self._build_class_subject_mappings(
                db=db,
                school_id=school_id,
                template_classes=template_classes,
                selected_lookup=selected_lookup,
                class_lookup=created_classes,
                subject_lookup=created_subjects,
            )

            # --------------------------------------------------
            # Create custom classes
            # --------------------------------------------------

            custom_classes = await self._create_custom_classes(
                db=db,
                school_id=school_id,
                payload=payload,
            )

            # --------------------------------------------------
            # Create custom subjects
            # --------------------------------------------------

            custom_subjects = await self._create_custom_subjects(
                db=db,
                school_id=school_id,
                payload=payload,
                class_lookup=created_classes,
                custom_classes=custom_classes,
            )

            # --------------------------------------------------
            # Commit
            # --------------------------------------------------

            await db.commit()

            setup = await self.get_school_setup(
                db=db,
                school_id=school_id,
            )

            return AcademicSetupSummaryResponse(
                setup=setup,
                classes_created=(len(created_classes) + len(custom_classes)),
                subjects_created=(len(created_subjects) + len(custom_subjects)),
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
            ) from exc

    # ==========================================================
    # VALIDATE REQUEST
    # ==========================================================

    def _validate_request(
        self,
        template_classes,
        payload: ConfigureAcademicSetupRequest,
    ) -> None:
        if not payload.classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one class must be selected.",
            )

        template_lookup = {cls.id: cls for cls in template_classes}

        class_names: set[str] = set()

        for school_class in payload.classes:
            # --------------------------------------------------
            # Duplicate class names
            # --------------------------------------------------

            class_name = school_class.name.strip().lower()

            if class_name in class_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate class '{school_class.name}'.",
                )

            class_names.add(class_name)

            # --------------------------------------------------
            # Template class
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Custom class
            # --------------------------------------------------

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
    # CLONE / REUSE TEMPLATE CLASSES
    # ==========================================================

    async def _clone_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_classes,
        selected_lookup,
    ):
        school_classes: dict[UUID, Class] = {}

        for template_class in template_classes:
            selected = selected_lookup.get(
                template_class.id,
            )

            if selected is None:
                continue

            if not selected["enabled"]:
                continue

            # --------------------------------------------------
            # Reuse an existing class if one already exists
            # for this school/template class.
            # --------------------------------------------------

            school_class = await self.repository.get_class_by_template_id(
                db,
                school_id,
                template_class.id,
            )

            if school_class is None:
                school_class = Class(
                    school_id=school_id,
                    template_class_id=template_class.id,
                    name=selected["name"],
                    level=selected["level"],
                    sort_order=template_class.sort_order,
                    is_custom=False,
                )

                await self.repository.create_class(
                    db,
                    school_class,
                )

            else:
                school_class.name = selected["name"]
                school_class.level = selected["level"]
                school_class.sort_order = template_class.sort_order
                school_class.is_custom = False

                await self.repository.update_class(
                    db,
                    school_class,
                )

            school_classes[template_class.id] = school_class

        return school_classes

    # ==========================================================
    # CLONE / REUSE TEMPLATE SUBJECTS
    # ==========================================================

    async def _clone_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_classes,
        selected_lookup,
    ):
        subjects: dict[UUID, Subject] = {}

        selected_subjects: dict[UUID, dict] = {}

        # Determine which template subjects are currently
        # selected anywhere in the configuration.

        for template_class in template_classes:
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

                # Keep the first selected version of a subject.
                if template_subject.id not in selected_subjects:
                    selected_subjects[template_subject.id] = {
                        "name": subject_selection["name"],
                        "code": template_subject.code,
                    }

        # ------------------------------------------------------
        # Reuse or create subjects
        # ------------------------------------------------------

        for template_subject_id, selection in selected_subjects.items():
            school_subject = await self.repository.get_subject_by_template_id(
                db,
                school_id,
                template_subject_id,
            )

            if school_subject is None:
                school_subject = Subject(
                    school_id=school_id,
                    template_subject_id=template_subject_id,
                    name=selection["name"],
                    code=selection["code"],
                    is_custom=False,
                )

                await self.repository.create_subject(
                    db,
                    school_subject,
                )

            else:
                # Preserve the subject ID so historical
                # result records remain valid.

                school_subject.name = selection["name"]
                school_subject.code = selection["code"]
                school_subject.is_custom = False

                await self.repository.update_subject(
                    db,
                    school_subject,
                )

            subjects[template_subject_id] = school_subject

        return subjects

    # ==========================================================
    # CREATE TEMPLATE CLASS-SUBJECT MAPPINGS
    # ==========================================================

    async def _build_class_subject_mappings(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_classes,
        selected_lookup,
        class_lookup,
        subject_lookup,
    ):
        mappings: list[ClassSubject] = []

        for template_class in template_classes:
            class_selection = selected_lookup.get(
                template_class.id,
            )

            if class_selection is None:
                continue

            if not class_selection["enabled"]:
                continue

            school_class = class_lookup.get(
                template_class.id,
            )

            if school_class is None:
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

                school_subject = subject_lookup.get(
                    template_subject.id,
                )

                if school_subject is None:
                    continue

                mappings.append(
                    ClassSubject(
                        school_id=school_id,
                        class_id=school_class.id,
                        subject_id=school_subject.id,
                    )
                )

        if mappings:
            await self.repository.bulk_create_mappings(
                db,
                mappings,
            )

        return mappings

    # ==========================================================
    # CREATE / REUSE CUSTOM CLASSES
    # ==========================================================

    async def _create_custom_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: ConfigureAcademicSetupRequest,
    ) -> dict[str, Class]:
        custom_classes: dict[str, Class] = {}

        for school_class in payload.classes:
            # Skip template classes.
            if school_class.template_class_id is not None:
                continue

            if not school_class.enabled:
                continue

            class_name = school_class.name.strip()

            # --------------------------------------------------
            # Reuse existing custom class by school + name.
            # --------------------------------------------------

            existing_class = await self.repository.get_class_by_name(
                db,
                school_id,
                class_name,
            )

            if existing_class is None:
                existing_class = Class(
                    school_id=school_id,
                    template_class_id=None,
                    name=class_name,
                    level=school_class.level,
                    sort_order=school_class.sort_order,
                    is_custom=True,
                )

                await self.repository.create_class(
                    db,
                    existing_class,
                )

            else:
                existing_class.level = school_class.level
                existing_class.sort_order = school_class.sort_order
                existing_class.is_custom = True

                await self.repository.update_class(
                    db,
                    existing_class,
                )

            custom_classes[class_name.lower()] = existing_class

        return custom_classes

    # ==========================================================
    # CREATE / REUSE CUSTOM SUBJECTS
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

            # --------------------------------------------------
            # Resolve school class
            # --------------------------------------------------

            if school_class.template_class_id:
                school_db_class = class_lookup.get(
                    school_class.template_class_id,
                )
            else:
                school_db_class = custom_classes.get(
                    school_class.name.strip().lower(),
                )

            if school_db_class is None:
                continue

            # --------------------------------------------------
            # Process custom subjects
            # --------------------------------------------------

            for subject in school_class.subjects:
                if not subject.enabled:
                    continue

                # Skip template subjects.
                if subject.template_subject_id:
                    continue

                key = subject.name.strip().lower()

                school_subject = created_subjects.get(key)

                if school_subject is None:
                    # --------------------------------------------------
                    # Reuse an existing custom subject by name.
                    # --------------------------------------------------

                    school_subject = await self.repository.get_subject_by_name(
                        db,
                        school_id,
                        subject.name.strip(),
                    )

                    if school_subject is None:
                        school_subject = Subject(
                            school_id=school_id,
                            template_subject_id=None,
                            name=subject.name.strip(),
                            code=subject.code,
                            is_custom=True,
                        )

                        await self.repository.create_subject(
                            db,
                            school_subject,
                        )

                    else:
                        school_subject.code = subject.code
                        school_subject.is_custom = True

                        await self.repository.update_subject(
                            db,
                            school_subject,
                        )

                    created_subjects[key] = school_subject

                # --------------------------------------------------
                # Create current mapping
                # --------------------------------------------------

                mappings.append(
                    ClassSubject(
                        school_id=school_id,
                        class_id=school_db_class.id,
                        subject_id=school_subject.id,
                    )
                )

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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found.",
            )

        if school_class.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found.",
            )

        if school_class.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete this class.",
            )

        await self.repository.remove_class_subjects(
            db,
            class_id,
        )

        try:
            await self.repository.delete_class(
                db,
                school_class,
            )

            await db.commit()

        except Exception as exc:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This class cannot be deleted because it is "
                    "already referenced by other academic records. "
                    "Remove those references first."
                ),
            ) from exc

        return {
            "message": "Class deleted successfully.",
        }

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found.",
            )

        if subject.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found.",
            )

        if subject.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete this subject.",
            )

        await self.repository.remove_subject_mappings(
            db,
            subject_id,
        )

        try:
            await self.repository.delete_subject(
                db,
                subject,
            )

            await db.commit()

        except Exception as exc:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This subject cannot be deleted because it is "
                    "already referenced by other academic records. "
                    "Remove those references first."
                ),
            ) from exc

        return {
            "message": "Subject deleted successfully.",
        }

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found.",
            )

        if school_class.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid class.",
            )

        # --------------------------------------------------
        # Verify all subjects before changing mappings.
        # --------------------------------------------------

        subjects = []

        for subject_id in payload.subject_ids:
            subject = await self.repository.get_subject(
                db,
                subject_id,
            )

            if not subject:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Subject {subject_id} not found.",
                )

            if subject.school_id != school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid subject.",
                )

            subjects.append(subject)

        # --------------------------------------------------
        # Replace mappings for this class.
        # --------------------------------------------------

        await self.repository.remove_class_subjects(
            db,
            class_id,
        )

        mappings = []

        for subject in subjects:
            mappings.append(
                ClassSubject(
                    school_id=school_id,
                    class_id=class_id,
                    subject_id=subject.id,
                )
            )

        if mappings:
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
        Update the school's academic configuration.

        IMPORTANT:

        This does NOT delete classes or subjects.

        Existing classes and subjects may be referenced by:
        • student_enrollments
        • result_records
        • attendance
        • lessons
        • other historical records

        Therefore:

        1. Existing Class records are reused.
        2. Existing Subject records are reused.
        3. New records are created when necessary.
        4. ClassSubject mappings are rebuilt.
        5. Historical records remain untouched.

        IMPORTANT TEMPLATE RULE:

        AcademicTemplate does not own unique ClassTemplate rows anymore.

        ClassTemplate is globally unique by:
            (name, level)

        Therefore template.class_templates MUST NOT be used here.

        Instead, the template's persisted levels are used to resolve
        all applicable ClassTemplate rows.
        """

        try:
            # --------------------------------------------------
            # Load template
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
            # IMPORTANT:
            #
            # Resolve all globally unique ClassTemplate rows
            # belonging to the levels supported by this
            # AcademicTemplate.
            #
            # Example:
            #
            # Nursery, Primary & Secondary
            #
            # template.levels =
            #     ["NURSERY", "PRIMARY", "SECONDARY"]
            #
            # Therefore this gets:
            #
            # Nursery 1-3
            # Primary 1-6
            # JSS1-3
            # SS1-3
            # --------------------------------------------------

            template_classes = await self.repository.get_template_classes(
                db=db,
                levels=template.levels,
            )

            # --------------------------------------------------
            # Validate payload
            # --------------------------------------------------

            self._validate_request(
                template_classes,
                payload,
            )

            # --------------------------------------------------
            # Remove ONLY current class-subject relationships.
            #
            # Do NOT remove classes.
            # Do NOT remove subjects.
            # --------------------------------------------------

            await self.repository.delete_school_mappings(
                db,
                school_id,
            )

            await db.flush()

            # --------------------------------------------------
            # Build lookup
            # --------------------------------------------------

            selected_lookup = self._build_selected_lookup(
                payload=payload,
            )

            # --------------------------------------------------
            # Reuse/create template classes
            # --------------------------------------------------

            class_lookup = await self._sync_template_classes(
                db=db,
                school_id=school_id,
                template_classes=template_classes,
                selected_lookup=selected_lookup,
            )

            # --------------------------------------------------
            # Reuse/create template subjects
            # --------------------------------------------------

            subject_lookup = await self._sync_template_subjects(
                db=db,
                school_id=school_id,
                template_classes=template_classes,
                selected_lookup=selected_lookup,
            )

            # --------------------------------------------------
            # Rebuild template mappings
            # --------------------------------------------------

            template_mappings = await self._build_class_subject_mappings(
                db=db,
                school_id=school_id,
                template_classes=template_classes,
                selected_lookup=selected_lookup,
                class_lookup=class_lookup,
                subject_lookup=subject_lookup,
            )

            # --------------------------------------------------
            # Reuse/create custom classes
            # --------------------------------------------------

            custom_classes = await self._sync_custom_classes(
                db=db,
                school_id=school_id,
                payload=payload,
            )

            # --------------------------------------------------
            # Reuse/create custom subjects and mappings
            # --------------------------------------------------

            custom_subjects = await self._sync_custom_subjects(
                db=db,
                school_id=school_id,
                payload=payload,
                class_lookup=class_lookup,
                custom_classes=custom_classes,
            )

            # --------------------------------------------------
            # Commit
            # --------------------------------------------------

            await db.commit()

            setup = await self.get_school_setup(
                db=db,
                school_id=school_id,
            )

            return AcademicSetupSummaryResponse(
                setup=setup,
                classes_created=(len(class_lookup) + len(custom_classes)),
                subjects_created=(len(subject_lookup) + len(custom_subjects)),
                mappings_created=len(template_mappings),
                message="Academic setup updated successfully.",
            )

        except HTTPException:
            await db.rollback()
            raise

        except Exception as exc:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    # ==========================================================
    # SYNC TEMPLATE CLASSES
    # ==========================================================

    async def _sync_template_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_classes,
        selected_lookup,
    ):
        class_lookup: dict[UUID, Class] = {}

        for template_class in template_classes:
            selected = selected_lookup.get(
                template_class.id,
            )

            if selected is None:
                continue

            if not selected["enabled"]:
                continue

            school_class = await self.repository.get_class_by_template_id(
                db,
                school_id,
                template_class.id,
            )

            if school_class is None:
                school_class = Class(
                    school_id=school_id,
                    template_class_id=template_class.id,
                    name=selected["name"],
                    level=selected["level"],
                    sort_order=template_class.sort_order,
                    is_custom=False,
                )

                await self.repository.create_class(
                    db,
                    school_class,
                )

            else:
                school_class.name = selected["name"]
                school_class.level = selected["level"]
                school_class.sort_order = template_class.sort_order
                school_class.is_custom = False

                await self.repository.update_class(
                    db,
                    school_class,
                )

            class_lookup[template_class.id] = school_class

        return class_lookup

    # ==========================================================
    # SYNC TEMPLATE SUBJECTS
    # ==========================================================

    async def _sync_template_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        template_classes,
        selected_lookup,
    ):
        subject_lookup: dict[UUID, Subject] = {}

        selected_subjects: dict[UUID, dict] = {}

        for template_class in template_classes:
            class_selection = selected_lookup.get(
                template_class.id,
            )

            if class_selection is None:
                continue

            if not class_selection["enabled"]:
                continue

            for relation in template_class.subjects:
                template_subject = relation.subject_template

                selection = class_selection["subjects"].get(
                    template_subject.id,
                )

                if selection is None:
                    continue

                if not selection["enabled"]:
                    continue

                if template_subject.id not in selected_subjects:
                    selected_subjects[template_subject.id] = {
                        "name": selection["name"],
                        "code": template_subject.code,
                    }

        for template_subject_id, selection in selected_subjects.items():
            school_subject = await self.repository.get_subject_by_template_id(
                db,
                school_id,
                template_subject_id,
            )

            if school_subject is None:
                school_subject = Subject(
                    school_id=school_id,
                    template_subject_id=template_subject_id,
                    name=selection["name"],
                    code=selection["code"],
                    is_custom=False,
                )

                await self.repository.create_subject(
                    db,
                    school_subject,
                )

            else:
                school_subject.name = selection["name"]
                school_subject.code = selection["code"]
                school_subject.is_custom = False

                await self.repository.update_subject(
                    db,
                    school_subject,
                )

            subject_lookup[template_subject_id] = school_subject

        return subject_lookup

    # ==========================================================
    # SYNC CUSTOM CLASSES
    # ==========================================================

    async def _sync_custom_classes(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: ConfigureAcademicSetupRequest,
    ) -> dict[str, Class]:
        custom_classes: dict[str, Class] = {}

        for school_class in payload.classes:
            if school_class.template_class_id is not None:
                continue

            if not school_class.enabled:
                continue

            class_name = school_class.name.strip()

            existing_class = await self.repository.get_class_by_name(
                db,
                school_id,
                class_name,
            )

            if existing_class is None:
                existing_class = Class(
                    school_id=school_id,
                    template_class_id=None,
                    name=class_name,
                    level=school_class.level,
                    sort_order=school_class.sort_order,
                    is_custom=True,
                )

                await self.repository.create_class(
                    db,
                    existing_class,
                )

            else:
                existing_class.level = school_class.level
                existing_class.sort_order = school_class.sort_order
                existing_class.is_custom = True

                await self.repository.update_class(
                    db,
                    existing_class,
                )

            custom_classes[class_name.lower()] = existing_class

        return custom_classes

    # ==========================================================
    # SYNC CUSTOM SUBJECTS
    # ==========================================================

    async def _sync_custom_subjects(
        self,
        db: AsyncSession,
        school_id: UUID,
        payload: ConfigureAcademicSetupRequest,
        class_lookup: dict,
        custom_classes: dict,
    ) -> dict[str, Subject]:
        custom_subjects: dict[str, Subject] = {}
        mappings: list[ClassSubject] = []

        for school_class in payload.classes:
            if not school_class.enabled:
                continue

            # --------------------------------------------------
            # Resolve class
            # --------------------------------------------------

            if school_class.template_class_id:
                school_db_class = class_lookup.get(
                    school_class.template_class_id,
                )

            else:
                school_db_class = custom_classes.get(
                    school_class.name.strip().lower(),
                )

            if school_db_class is None:
                continue

            # --------------------------------------------------
            # Process custom subjects
            # --------------------------------------------------

            for subject in school_class.subjects:
                if not subject.enabled:
                    continue

                if subject.template_subject_id:
                    continue

                key = subject.name.strip().lower()

                school_subject = custom_subjects.get(key)

                if school_subject is None:
                    school_subject = await self.repository.get_subject_by_name(
                        db,
                        school_id,
                        subject.name.strip(),
                    )

                    if school_subject is None:
                        school_subject = Subject(
                            school_id=school_id,
                            template_subject_id=None,
                            name=subject.name.strip(),
                            code=subject.code,
                            is_custom=True,
                        )

                        await self.repository.create_subject(
                            db,
                            school_subject,
                        )

                    else:
                        school_subject.code = subject.code
                        school_subject.is_custom = True

                        await self.repository.update_subject(
                            db,
                            school_subject,
                        )

                    custom_subjects[key] = school_subject

                mappings.append(
                    ClassSubject(
                        school_id=school_id,
                        class_id=school_db_class.id,
                        subject_id=school_subject.id,
                    )
                )

        if mappings:
            await self.repository.bulk_create_mappings(
                db,
                mappings,
            )

        return custom_subjects

    # ==========================================================
    # RESET SCHOOL SETUP
    # ==========================================================

    async def reset_setup(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        """
        Reset the current academic configuration.

        This intentionally removes ONLY ClassSubject mappings.

        Classes and subjects are preserved because they may already
        be referenced by historical/operational records.
        """

        try:
            await self.repository.clear_school_setup(
                db,
                school_id,
            )

            await db.commit()

        except Exception as exc:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        return {
            "message": "Academic setup mappings have been reset successfully.",
            "configured": False,
        }


# ==========================================================
# SERVICE INSTANCE
# ==========================================================

academic_setup_service = AcademicSetupService()
