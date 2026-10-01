from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_template import AcademicTemplate
from app.models.class_template import ClassTemplate
from app.models.subject_template import SubjectTemplate
from app.models.template_class_subject import TemplateClassSubject

# ============================================================
# ACADEMIC TEMPLATES
# ============================================================

ACADEMIC_TEMPLATES = [
    {
        "name": "Nursery & Primary",
        "description": "Nursery and primary school academic structure.",
        "levels": ["NURSERY", "PRIMARY"],
    },
    {
        "name": "Secondary",
        "description": "Junior and senior secondary school academic structure.",
        "levels": ["SECONDARY"],
    },
    {
        "name": "Primary",
        "description": "Primary school academic structure.",
        "levels": ["PRIMARY"],
    },
    {
        "name": "Nursery, Primary & Secondary",
        "description": (
            "Complete nursery, primary, junior secondary and "
            "senior secondary school academic structure."
        ),
        "levels": ["NURSERY", "PRIMARY", "SECONDARY"],
    },
]


# ============================================================
# CLASS TEMPLATES
# ============================================================

CLASS_TEMPLATES = [
    ("Nursery 1", "NURSERY"),
    ("Nursery 2", "NURSERY"),
    ("Nursery 3", "NURSERY"),
    ("Primary 1", "PRIMARY"),
    ("Primary 2", "PRIMARY"),
    ("Primary 3", "PRIMARY"),
    ("Primary 4", "PRIMARY"),
    ("Primary 5", "PRIMARY"),
    ("Primary 6", "PRIMARY"),
    ("JSS1", "SECONDARY"),
    ("JSS2", "SECONDARY"),
    ("JSS3", "SECONDARY"),
    ("SS1", "SECONDARY"),
    ("SS2", "SECONDARY"),
    ("SS3", "SECONDARY"),
]


# ============================================================
# SUBJECTS
# ============================================================

# ------------------------------------------------------------
# NURSERY
# ------------------------------------------------------------
#
# THIS is the list that controls what the Nursery template
# should contain.
#
# Add/remove subjects here.
#
# IMPORTANT:
# If you are RENAMING an existing subject, also add the rename
# inside NURSERY_SUBJECT_RENAMES below.
#
# Example:
#
#     "English Language": "English & Communication"
#
# The existing database record will be renamed instead of
# creating another SubjectTemplate.
# ------------------------------------------------------------

NURSERY_SUBJECTS = [
    "English Language",
    "Mathematics",
    "Rhymes",
    "Phonics",
    "Colouring",
    "Writing",
    "Drawing",
    "Social Habits",
    "Health Education",
    "Creative Arts",
]


# ============================================================
# NURSERY SUBJECT RENAMES
# ============================================================
#
# Format:
#
#     "CURRENT DATABASE NAME": "NEW NAME"
#
# The existing SubjectTemplate ID is preserved.
#
# Example:
#
#     "English Language": "English & Communication",
#
# Do NOT add the new name to NURSERY_SUBJECTS without also
# adding the old -> new mapping here.
# ============================================================

NURSERY_SUBJECT_RENAMES: dict[str, str] = {
    "English Language": "Literacy",
    "Health Education": "Health Habits",
    "Mathematics": "Numeracy",
    "Writing": "Handwriting",
    "Creative Arts": "Pre-science",
}


# ============================================================
# NURSERY SUBJECTS TO REMOVE
# ============================================================
#
# Put subjects here when you no longer want them in the
# Nursery template.
#
# Example:
#
#     NURSERY_SUBJECTS_TO_REMOVE = {
#         "Rhymes",
#         "Colouring",
#     }
#
# The SubjectTemplate itself is NOT blindly deleted.
#
# Instead:
# 1. Nursery class mappings are removed.
# 2. SubjectTemplate.is_active is set to False.
#
# This protects existing school records that may already
# reference the SubjectTemplate.
# ============================================================

NURSERY_SUBJECTS_TO_REMOVE: set[str] = {}


# ============================================================
# PRIMARY SUBJECTS
# ============================================================

PRIMARY_SUBJECTS = [
    "English",
    "Mathematics",
    "Basic Science",
    "Social Studies",
    "Computer Studies",
    "CRS",
    "Agricultural Science",
    "CCA",
    "Verbal Reasoning",
    "Quantitative Reasoning",
    "Pre-Vocational Studies",
    "Basic Digital Literacy",
    "Physical and Health Education",
    "Nigerian History",
]


# ============================================================
# SECONDARY SUBJECTS
# ============================================================

SECONDARY_SUBJECTS = [
    "English",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Economics",
    "Government",
    "Commerce",
    "Agricultural Science",
    "ICT",
    "Pre-Vocational Studies",
    "Basic Digital Literacy",
    "Social and Citizenship Studies",
    "Nigerian History",
]


SUBJECTS_BY_LEVEL = {
    "NURSERY": NURSERY_SUBJECTS,
    "PRIMARY": PRIMARY_SUBJECTS,
    "SECONDARY": SECONDARY_SUBJECTS,
}


# ============================================================
# SPECIAL TEMPLATE CONFIGURATION
# ============================================================

NURSERY_TEMPLATE_NAME = "Nursery & Primary"


# ============================================================
# HELPERS
# ============================================================


async def get_or_create_template(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
) -> AcademicTemplate:
    """
    Get an existing AcademicTemplate by name.

    IMPORTANT:
    This never creates another template when one already exists.
    """

    result = await db.execute(
        select(AcademicTemplate).where(AcademicTemplate.name == name)
    )

    template = result.scalar_one_or_none()

    if template:
        return template

    template = AcademicTemplate(
        name=name,
        description=description,
    )

    db.add(template)

    await db.flush()

    return template


async def get_or_create_class(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    name: str,
    level: str,
    sort_order: int,
) -> ClassTemplate:
    """
    Get an existing ClassTemplate by name + level.

    Existing ClassTemplate IDs are preserved.

    The academic_template_id is intentionally NOT used to
    identify an existing class because your current database
    design treats classes such as Nursery 1 as shared records.
    """

    result = await db.execute(
        select(ClassTemplate).where(
            ClassTemplate.name == name,
            ClassTemplate.level == level,
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        return existing

    school_class = ClassTemplate(
        academic_template_id=template.id,
        name=name,
        level=level,
        sort_order=sort_order,
        is_active=True,
    )

    db.add(school_class)

    await db.flush()

    return school_class


async def get_subject_by_name_and_level(
    db: AsyncSession,
    *,
    name: str,
    level: str,
) -> SubjectTemplate | None:
    """
    Find an existing SubjectTemplate by name + level.

    This is used for normal seed operations.
    """

    result = await db.execute(
        select(SubjectTemplate).where(
            SubjectTemplate.name == name,
            SubjectTemplate.level == level,
        )
    )

    return result.scalar_one_or_none()


async def get_or_create_subject(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    name: str,
    level: str,
) -> SubjectTemplate:
    """
    Get an existing SubjectTemplate or create one.

    Existing IDs are preserved.
    """

    existing = await get_subject_by_name_and_level(
        db,
        name=name,
        level=level,
    )

    if existing:
        # If a previously removed subject is being added again,
        # reactivate it.
        if not existing.is_active:
            existing.is_active = True

        return existing

    subject = SubjectTemplate(
        academic_template_id=template.id,
        name=name,
        level=level,
        is_active=True,
    )

    db.add(subject)

    await db.flush()

    return subject


async def get_class_subject_mapping(
    db: AsyncSession,
    *,
    class_id,
    subject_id,
) -> TemplateClassSubject | None:
    """
    Get an existing class ↔ subject mapping.
    """

    result = await db.execute(
        select(TemplateClassSubject).where(
            TemplateClassSubject.class_template_id == class_id,
            TemplateClassSubject.subject_template_id == subject_id,
        )
    )

    return result.scalar_one_or_none()


async def map_subject(
    db: AsyncSession,
    *,
    school_class: ClassTemplate,
    subject: SubjectTemplate,
) -> TemplateClassSubject:
    """
    Create a class ↔ subject mapping only when it doesn't exist.
    """

    existing = await get_class_subject_mapping(
        db,
        class_id=school_class.id,
        subject_id=subject.id,
    )

    if existing:
        return existing

    mapping = TemplateClassSubject(
        class_template_id=school_class.id,
        subject_template_id=subject.id,
    )

    db.add(mapping)

    await db.flush()

    return mapping


# ============================================================
# NURSERY SUBJECT RENAME
# ============================================================


async def rename_nursery_subject(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    old_name: str,
    new_name: str,
) -> SubjectTemplate | None:
    """
    Rename an existing Nursery SubjectTemplate IN PLACE.

    The existing SubjectTemplate ID is preserved.

    This function deliberately does NOT create a new subject.

    It also checks whether another subject already exists with
    the requested new name. If it does, the rename is skipped
    to prevent duplicate/conflicting subjects.
    """

    if old_name == new_name:
        return await get_subject_by_name_and_level(
            db,
            name=old_name,
            level="NURSERY",
        )

    old_result = await db.execute(
        select(SubjectTemplate).where(
            SubjectTemplate.name == old_name,
            SubjectTemplate.level == "NURSERY",
        )
    )

    old_subject = old_result.scalar_one_or_none()

    if not old_subject:
        print(f"  Rename skipped: Nursery subject '{old_name}' was not found.")

        return None

    # --------------------------------------------------------
    # Check whether the target name already exists
    # --------------------------------------------------------

    new_result = await db.execute(
        select(SubjectTemplate).where(
            SubjectTemplate.name == new_name,
            SubjectTemplate.level == "NURSERY",
        )
    )

    new_subject = new_result.scalar_one_or_none()

    if new_subject and new_subject.id != old_subject.id:
        print(
            f"  Rename skipped: '{new_name}' already exists as another Nursery subject."
        )

        return old_subject

    # --------------------------------------------------------
    # Rename existing row
    # --------------------------------------------------------

    old_subject.name = new_name
    old_subject.is_active = True

    await db.flush()

    print(
        f"  Subject renamed: "
        f"'{old_name}' -> '{new_name}' "
        f"(ID preserved: {old_subject.id})"
    )

    return old_subject


# ============================================================
# REMOVE NURSERY SUBJECT
# ============================================================


async def remove_nursery_subject(
    db: AsyncSession,
    *,
    subject_name: str,
    nursery_classes: list[ClassTemplate],
) -> None:
    """
    Remove a subject from Nursery classes without blindly
    deleting the SubjectTemplate database row.

    Steps:
    1. Find the Nursery SubjectTemplate.
    2. Remove its Nursery class mappings.
    3. Mark SubjectTemplate as inactive.

    The SubjectTemplate ID remains available for historical
    records that may already reference it.
    """

    result = await db.execute(
        select(SubjectTemplate).where(
            SubjectTemplate.name == subject_name,
            SubjectTemplate.level == "NURSERY",
        )
    )

    subject = result.scalar_one_or_none()

    if not subject:
        print(f"  Remove skipped: Nursery subject '{subject_name}' was not found.")

        return

    removed_mappings = 0

    for school_class in nursery_classes:
        mapping_result = await db.execute(
            select(TemplateClassSubject).where(
                TemplateClassSubject.class_template_id == school_class.id,
                TemplateClassSubject.subject_template_id == subject.id,
            )
        )

        mapping = mapping_result.scalar_one_or_none()

        if mapping:
            await db.delete(mapping)
            removed_mappings += 1

    # --------------------------------------------------------
    # Do NOT delete the SubjectTemplate itself.
    #
    # Existing school results or other historical data may
    # reference this ID.
    # --------------------------------------------------------

    subject.is_active = False

    await db.flush()

    print(
        f"  Nursery subject removed: '{subject_name}' "
        f"({removed_mappings} mappings removed)"
    )


# ============================================================
# RECONCILE NURSERY SUBJECTS
# ============================================================


async def reconcile_nursery_subjects(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    nursery_classes: list[ClassTemplate],
) -> None:
    """
    Reconcile the existing Nursery template with the current
    configuration.

    This is the important part of the new seeder.

    It allows you to:

    - rename existing subjects
    - remove subjects
    - add new subjects
    - preserve existing subject IDs
    - avoid duplicate SubjectTemplate rows
    - preserve existing class IDs
    """

    print("\n  Nursery subject reconciliation")

    # --------------------------------------------------------
    # 1. RENAME EXISTING SUBJECTS
    # --------------------------------------------------------

    for old_name, new_name in NURSERY_SUBJECT_RENAMES.items():
        await rename_nursery_subject(
            db,
            template=template,
            old_name=old_name,
            new_name=new_name,
        )

    # --------------------------------------------------------
    # 2. REMOVE SUBJECTS
    # --------------------------------------------------------

    for subject_name in NURSERY_SUBJECTS_TO_REMOVE:
        await remove_nursery_subject(
            db,
            subject_name=subject_name,
            nursery_classes=nursery_classes,
        )

    # --------------------------------------------------------
    # 3. CREATE / RESTORE REQUIRED SUBJECTS
    # --------------------------------------------------------

    subjects: dict[str, SubjectTemplate] = {}

    for subject_name in NURSERY_SUBJECTS:
        subject = await get_or_create_subject(
            db,
            template=template,
            name=subject_name,
            level="NURSERY",
        )

        subjects[subject_name] = subject

    # --------------------------------------------------------
    # 4. ENSURE REQUIRED SUBJECT MAPPINGS
    # --------------------------------------------------------

    mappings_created = 0

    for school_class in nursery_classes:
        for subject in subjects.values():
            existing = await get_class_subject_mapping(
                db,
                class_id=school_class.id,
                subject_id=subject.id,
            )

            if existing:
                continue

            db.add(
                TemplateClassSubject(
                    class_template_id=school_class.id,
                    subject_template_id=subject.id,
                )
            )

            mappings_created += 1

    await db.flush()

    print(f"  Nursery subjects active: {len(subjects)}")

    print(f"  Nursery mappings created: {mappings_created}")


# ============================================================
# NORMAL SUBJECT RECONCILIATION
# ============================================================


async def ensure_level_subjects(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    level: str,
) -> dict[str, SubjectTemplate]:
    """
    Ensure normal Primary / Secondary subjects exist.

    Unlike Nursery, these subjects are not modified or removed
    by the seeder.
    """

    subjects: dict[str, SubjectTemplate] = {}

    subject_names = SUBJECTS_BY_LEVEL.get(level, [])

    for subject_name in subject_names:
        subject = await get_or_create_subject(
            db,
            template=template,
            name=subject_name,
            level=level,
        )

        subjects[subject_name] = subject

    return subjects


# ============================================================
# NORMAL CLASS-SUBJECT MAPPING
# ============================================================


async def ensure_class_subject_mappings(
    db: AsyncSession,
    *,
    template_classes: dict[str, ClassTemplate],
    subjects_by_level: dict[str, list[SubjectTemplate]],
) -> int:
    """
    Ensure all required class ↔ subject mappings exist.
    """

    mappings_created = 0

    for class_name, school_class in template_classes.items():
        level = school_class.level

        subjects = subjects_by_level.get(level, [])

        for subject in subjects:
            existing = await get_class_subject_mapping(
                db,
                class_id=school_class.id,
                subject_id=subject.id,
            )

            if existing:
                continue

            db.add(
                TemplateClassSubject(
                    class_template_id=school_class.id,
                    subject_template_id=subject.id,
                )
            )

            mappings_created += 1

    await db.flush()

    return mappings_created


# ============================================================
# MAIN SEEDER
# ============================================================


async def seed_academic_templates(
    db: AsyncSession,
) -> None:
    """
    Non-destructive academic template seed + Nursery
    reconciliation.

    ------------------------------------------------------------
    SAFETY
    ------------------------------------------------------------

    This function:

    - Does NOT create duplicate AcademicTemplates.
    - Does NOT recreate existing ClassTemplates.
    - Preserves existing ClassTemplate IDs.
    - Preserves existing SubjectTemplate IDs when renaming.
    - Does NOT blindly delete SubjectTemplate records.
    - Removes obsolete Nursery mappings safely.
    - Creates only genuinely missing subjects/mappings.
    - Keeps existing school records intact.
    """

    print("\n")
    print("=" * 70)
    print("ACADEMIC TEMPLATE SEED / RECONCILIATION")
    print("=" * 70)

    # ========================================================
    # 1. GET / CREATE ACADEMIC TEMPLATES
    # ========================================================

    templates_by_name: dict[str, AcademicTemplate] = {}

    for template_data in ACADEMIC_TEMPLATES:
        template = await get_or_create_template(
            db,
            name=template_data["name"],
            description=template_data["description"],
        )

        templates_by_name[template.name] = template

    print(f"\nAcademic templates ensured: {len(templates_by_name)}")

    # ========================================================
    # 2. PROCESS EACH TEMPLATE
    # ========================================================

    for template_data in ACADEMIC_TEMPLATES:
        template = templates_by_name[template_data["name"]]

        allowed_levels = set(template_data["levels"])

        print("\n" + "-" * 70)
        print(f"Template: {template.name}")
        print("-" * 70)

        # ====================================================
        # CLASSES
        # ====================================================

        template_classes: dict[str, ClassTemplate] = {}

        for sort_order, (class_name, level) in enumerate(
            CLASS_TEMPLATES,
            start=1,
        ):
            if level not in allowed_levels:
                continue

            school_class = await get_or_create_class(
                db,
                template=template,
                name=class_name,
                level=level,
                sort_order=sort_order,
            )

            template_classes[class_name] = school_class

        print(f"  Classes ensured: {len(template_classes)}")

        # ====================================================
        # NURSERY
        # ====================================================

        if template.name == NURSERY_TEMPLATE_NAME and "NURSERY" in allowed_levels:
            nursery_classes = [
                school_class
                for school_class in template_classes.values()
                if school_class.level == "NURSERY"
            ]

            await reconcile_nursery_subjects(
                db,
                template=template,
                nursery_classes=nursery_classes,
            )

        # ====================================================
        # PRIMARY / SECONDARY SUBJECTS
        # ====================================================

        subjects_by_level: dict[
            str,
            list[SubjectTemplate],
        ] = {}

        for level in allowed_levels:
            # Nursery was already reconciled above.
            if template.name == NURSERY_TEMPLATE_NAME and level == "NURSERY":
                continue

            subjects = await ensure_level_subjects(
                db,
                template=template,
                level=level,
            )

            subjects_by_level[level] = list(subjects.values())

        # ====================================================
        # CLASS ↔ SUBJECT MAPPINGS
        # ====================================================

        if subjects_by_level:
            mappings_created = await ensure_class_subject_mappings(
                db,
                template_classes=template_classes,
                subjects_by_level=subjects_by_level,
            )

            print(f"  Subject mappings created: {mappings_created}")

    # ========================================================
    # 3. COMMIT
    # ========================================================

    await db.commit()

    print("\n")
    print("=" * 70)
    print("ACADEMIC TEMPLATE SEED / RECONCILIATION COMPLETED")
    print("=" * 70)
    print("\n")
