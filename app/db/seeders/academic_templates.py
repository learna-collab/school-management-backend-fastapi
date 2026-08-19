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
        "description": "Complete nursery, primary, junior secondary and senior secondary structure.",
        "levels": ["NURSERY", "PRIMARY", "SECONDARY"],
    },
]


# ============================================================
# CLASS DEFINITIONS
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
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        return existing

    subject = SubjectTemplate(
        academic_template_id=template.id,
        name=name,
        level=level,
    )

    db.add(subject)

    await db.flush()

    return subject


async def map_subject(
    db: AsyncSession,
    *,
    school_class: ClassTemplate,
    subject: SubjectTemplate,
):
    result = await db.execute(
        select(TemplateClassSubject).where(
            TemplateClassSubject.class_template_id == school_class.id,
            TemplateClassSubject.subject_template_id == subject.id,
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        return

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
    # ========================================================
    # CREATE ALL FOUR TEMPLATES
    # ========================================================

    templates: dict[str, AcademicTemplate] = {}

    for definition in ACADEMIC_TEMPLATES:
        template = await get_or_create_template(
            db,
            name=definition["name"],
            description=definition["description"],
        )

        templates[definition["name"]] = template

    # ========================================================
    # CREATE CLASSES FOR EACH TEMPLATE
    # ========================================================

    for definition in ACADEMIC_TEMPLATES:
        template = templates[definition["name"]]

        sort_order = 1

        for class_name, level in CLASS_TEMPLATES:
            if level not in definition["levels"]:
                continue

            await get_or_create_class(
                db,
                template=template,
                name=class_name,
                level=level,
                sort_order=sort_order,
            )

            sort_order += 1

    # ========================================================
    # CREATE SUBJECTS FOR EACH TEMPLATE
    # ========================================================

    subject_definitions = {
        "NURSERY": NURSERY_SUBJECTS,
        "PRIMARY": PRIMARY_SUBJECTS,
        "SECONDARY": SECONDARY_SUBJECTS,
    }

    for definition in ACADEMIC_TEMPLATES:
        template = templates[definition["name"]]

        for level in definition["levels"]:
            for subject_name in subject_definitions[level]:
                await get_or_create_subject(
                    db,
                    template=template,
                    name=subject_name,
                    level=level,
                )

    # ========================================================
    # MAP CLASSES TO SUBJECTS
    # ========================================================

    for definition in ACADEMIC_TEMPLATES:
        template = templates[definition["name"]]

        # Get classes belonging to this template
        class_result = await db.execute(
            select(ClassTemplate).where(
                ClassTemplate.academic_template_id == template.id
            )
        )

        classes = class_result.scalars().all()

        # Get subjects belonging to this template
        subject_result = await db.execute(
            select(SubjectTemplate).where(
                SubjectTemplate.academic_template_id == template.id
            )
        )

        subjects = subject_result.scalars().all()

        # Group subjects by level
        subjects_by_level: dict[str, list[SubjectTemplate]] = {
            "NURSERY": [],
            "PRIMARY": [],
            "SECONDARY": [],
        }

        for subject in subjects:
            subjects_by_level[subject.level].append(subject)

        # Map subjects to their corresponding classes
        for school_class in classes:
            class_subjects = subjects_by_level.get(
                school_class.level,
                [],
            )

            for subject in class_subjects:
                await map_subject(
                    db,
                    school_class=school_class,
                    subject=subject,
                )

    # ========================================================
    # COMMIT
    # ========================================================

    await db.commit()

    print("=" * 60)
    print("Academic templates seeded successfully.")
    print("=" * 60)

    for definition in ACADEMIC_TEMPLATES:
        template = templates[definition["name"]]

        print(f"✓ {template.name}: {', '.join(definition['levels'])}")

    print("=" * 60)
