from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_template import AcademicTemplate
from app.models.class_template import ClassTemplate
from app.models.subject_template import SubjectTemplate
from app.models.template_class_subject import TemplateClassSubject

# ============================================================
# ACADEMIC TEMPLATE DEFINITIONS
# ============================================================

ACADEMIC_TEMPLATES = [
    {
        "name": "Nigerian Basic Education",
        "description": "NERDC Curriculum",
    }
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
]


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
    Returns an existing academic template
    or creates a new one.
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


async def create_class(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    name: str,
    level: str,
    sort_order: int,
) -> ClassTemplate:
    """
    Creates one class template.
    """

    item = ClassTemplate(
        academic_template_id=template.id,
        name=name,
        level=level,
        sort_order=sort_order,
    )

    db.add(item)

    await db.flush()

    return item


async def create_subject(
    db: AsyncSession,
    *,
    template: AcademicTemplate,
    name: str,
    level: str,
) -> SubjectTemplate:
    """
    Creates one subject template.
    """

    item = SubjectTemplate(
        academic_template_id=template.id,
        name=name,
        level=level,
    )

    db.add(item)

    await db.flush()

    return item


async def map_subject(
    db: AsyncSession,
    *,
    school_class: ClassTemplate,
    subject: SubjectTemplate,
):
    """
    Creates a class-subject mapping.
    """

    mapping = TemplateClassSubject(
        class_template_id=school_class.id,
        subject_template_id=subject.id,
    )

    db.add(mapping)


# ============================================================
# MAIN SEEDER
# ============================================================


async def seed_academic_templates(
    db: AsyncSession,
):
    """
    Seeds the default academic template together
    with all class templates, subject templates,
    and class-subject mappings.

    Safe to run multiple times.
    """

    # -----------------------------------------
    # Check if template already exists
    # -----------------------------------------

    result = await db.execute(
        select(AcademicTemplate).where(
            AcademicTemplate.name == "Nigerian Basic Education"
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        print("✓ Academic template already seeded.")
        return

    # -----------------------------------------
    # Create Template
    # -----------------------------------------

    template = await get_or_create_template(
        db,
        name="Nigerian Basic Education",
        description="NERDC Curriculum",
    )

    # -----------------------------------------
    # Dictionaries
    # -----------------------------------------

    class_lookup: dict[str, ClassTemplate] = {}

    nursery_subject_lookup: dict[str, SubjectTemplate] = {}

    primary_subject_lookup: dict[str, SubjectTemplate] = {}

    secondary_subject_lookup: dict[str, SubjectTemplate] = {}

    # -----------------------------------------
    # Create Classes
    # -----------------------------------------

    for index, (name, level) in enumerate(
        CLASS_TEMPLATES,
        start=1,
    ):
        school_class = await create_class(
            db=db,
            template=template,
            name=name,
            level=level,
            sort_order=index,
        )

        class_lookup[name] = school_class

    # -----------------------------------------
    # Nursery Subjects
    # -----------------------------------------

    for subject_name in NURSERY_SUBJECTS:
        subject = await create_subject(
            db=db,
            template=template,
            name=subject_name,
            level="NURSERY",
        )

        nursery_subject_lookup[subject_name] = subject

    # -----------------------------------------
    # Primary Subjects
    # -----------------------------------------

    for subject_name in PRIMARY_SUBJECTS:
        subject = await create_subject(
            db=db,
            template=template,
            name=subject_name,
            level="PRIMARY",
        )

        primary_subject_lookup[subject_name] = subject

    # -----------------------------------------
    # Secondary Subjects
    # -----------------------------------------

    for subject_name in SECONDARY_SUBJECTS:
        subject = await create_subject(
            db=db,
            template=template,
            name=subject_name,
            level="SECONDARY",
        )

        secondary_subject_lookup[subject_name] = subject

    # =====================================================
    # PART 3 CONTINUES HERE...
    # =====================================================
    # =====================================================
    # MAP NURSERY SUBJECTS
    # =====================================================

    nursery_classes = [
        "Nursery 1",
        "Nursery 2",
        "Nursery 3",
    ]

    for class_name in nursery_classes:
        school_class = class_lookup[class_name]

        for subject in nursery_subject_lookup.values():
            await map_subject(
                db=db,
                school_class=school_class,
                subject=subject,
            )

    # =====================================================
    # MAP PRIMARY SUBJECTS
    # =====================================================

    primary_classes = [
        "Primary 1",
        "Primary 2",
        "Primary 3",
        "Primary 4",
        "Primary 5",
        "Primary 6",
    ]

    for class_name in primary_classes:
        school_class = class_lookup[class_name]

        for subject in primary_subject_lookup.values():
            await map_subject(
                db=db,
                school_class=school_class,
                subject=subject,
            )

    # =====================================================
    # MAP SECONDARY SUBJECTS
    # =====================================================

    secondary_classes = [
        "JSS1",
        "JSS2",
        "JSS3",
        "SS1",
        "SS2",
        "SS3",
    ]

    for class_name in secondary_classes:
        school_class = class_lookup[class_name]

        for subject in secondary_subject_lookup.values():
            await map_subject(
                db=db,
                school_class=school_class,
                subject=subject,
            )

    # =====================================================
    # COMMIT
    # =====================================================

    await db.commit()

    print("=" * 60)
    print("Academic templates seeded successfully.")
    print(f"Template : {template.name}")
    print(f"Classes  : {len(class_lookup)}")
    print(
        "Subjects :",
        len(nursery_subject_lookup)
        + len(primary_subject_lookup)
        + len(secondary_subject_lookup),
    )
    print("=" * 60)
