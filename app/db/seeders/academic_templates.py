from sqlalchemy import select
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
# HELPERS
# ============================================================


async def get_or_create_template(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
) -> AcademicTemplate:
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
    Non-destructive.

    Looks for the class ONLY inside the specified academic
    template.

    Existing ClassTemplate rows are never deleted or replaced.
    """

    result = await db.execute(
        select(ClassTemplate).where(
            ClassTemplate.academic_template_id == template.id,
            ClassTemplate.name == name,
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


async def get_or_create_subject(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    name: str,
    level: str,
) -> SubjectTemplate:
    result = await db.execute(
        select(SubjectTemplate).where(
            SubjectTemplate.academic_template_id == template.id,
            SubjectTemplate.name == name,
            SubjectTemplate.level == level,
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
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


async def map_subject(
    db: AsyncSession,
    *,
    school_class: ClassTemplate,
    subject: SubjectTemplate,
) -> TemplateClassSubject:
    """
    Creates a class-subject mapping only if it does not already exist.
    """

    result = await db.execute(
        select(TemplateClassSubject).where(
            TemplateClassSubject.class_template_id == school_class.id,
            TemplateClassSubject.subject_template_id == subject.id,
        )
    )

    existing = result.scalar_one_or_none()

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
# MAIN SEEDER
# ============================================================


async def seed_academic_templates(
    db: AsyncSession,
) -> None:
    """
    Non-destructive academic template repair/seed.

    IMPORTANT:
    - Does NOT delete AcademicTemplate rows.
    - Does NOT delete ClassTemplate rows.
    - Does NOT recreate existing ClassTemplate rows.
    - Existing ClassTemplate IDs are preserved.
    - Safe for existing school Class records that reference
      class_templates.id.
    - Creates only missing classes, subjects and mappings.
    """

    print("\n")
    print("=" * 60)
    print("ACADEMIC TEMPLATE SEED")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Create/get academic templates
    # --------------------------------------------------------

    templates_by_name: dict[str, AcademicTemplate] = {}

    for template_data in ACADEMIC_TEMPLATES:
        template = await get_or_create_template(
            db,
            name=template_data["name"],
            description=template_data["description"],
        )

        templates_by_name[template.name] = template

    # --------------------------------------------------------
    # 2. Create/get classes, subjects and mappings
    # --------------------------------------------------------

    for template_data in ACADEMIC_TEMPLATES:
        template = templates_by_name[template_data["name"]]
        allowed_levels = set(template_data["levels"])

        print(f"\nTemplate: {template.name}")

        # ----------------------------------------------------
        # Classes
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Subjects
        # ----------------------------------------------------

        subjects_by_level: dict[
            str,
            list[SubjectTemplate],
        ] = {}

        for level in allowed_levels:
            subject_names = SUBJECTS_BY_LEVEL.get(level, [])

            subjects_by_level[level] = []

            for subject_name in subject_names:
                subject = await get_or_create_subject(
                    db,
                    template=template,
                    name=subject_name,
                    level=level,
                )

                subjects_by_level[level].append(subject)

        # ----------------------------------------------------
        # Class ↔ Subject mappings
        # ----------------------------------------------------

        mappings_created = 0

        for class_name, school_class in template_classes.items():
            level = school_class.level

            subjects = subjects_by_level.get(level, [])

            for subject in subjects:
                result = await db.execute(
                    select(TemplateClassSubject).where(
                        TemplateClassSubject.class_template_id == school_class.id,
                        TemplateClassSubject.subject_template_id == subject.id,
                    )
                )

                existing = result.scalar_one_or_none()

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

        print(f"  Subject mappings created: {mappings_created}")

    # --------------------------------------------------------
    # 3. Commit
    # --------------------------------------------------------

    await db.commit()

    print("\n")
    print("=" * 60)
    print("ACADEMIC TEMPLATE SEED COMPLETED")
    print("=" * 60)
