import asyncio

from sqlalchemy import select

from app.db.database import async_session_local
from app.models.academic_template import AcademicTemplate
from app.models.class_template import ClassTemplate
from app.models.subject_template import SubjectTemplate
from app.models.template_class_subject import TemplateClassSubject

MISSING_SECONDARY_SUBJECTS = [
    "English",
    "Mathematics",
    "Agricultural Science",
    "Pre-Vocational Studies",
    "Basic Digital Literacy",
    "Social and Citizenship Studies",
    "Nigerian History",
]


async def get_or_create_secondary_subject(db, template, name):
    result = await db.execute(
        select(SubjectTemplate).where(
            SubjectTemplate.academic_template_id == template.id,
            SubjectTemplate.name == name,
            SubjectTemplate.level == "SECONDARY",
        )
    )

    subject = result.scalar_one_or_none()

    if subject:
        return subject

    subject = SubjectTemplate(
        academic_template_id=template.id,
        name=name,
        level="SECONDARY",
    )

    db.add(subject)
    await db.flush()
    return subject


async def map_subject_to_secondary_classes(db, template, subject):
    result = await db.execute(
        select(ClassTemplate).where(
            ClassTemplate.academic_template_id == template.id,
            ClassTemplate.level == "SECONDARY",
        )
    )

    classes = result.scalars().all()

    for school_class in classes:
        exists = await db.execute(
            select(TemplateClassSubject).where(
                TemplateClassSubject.class_template_id == school_class.id,
                TemplateClassSubject.subject_template_id == subject.id,
            )
        )

        if exists.scalar_one_or_none():
            continue

        db.add(
            TemplateClassSubject(
                class_template_id=school_class.id,
                subject_template_id=subject.id,
            )
        )


async def main():
    async with async_session_local() as db:
        result = await db.execute(select(AcademicTemplate))
        templates = result.scalars().all()

        for template in templates:
            secondary_classes = await db.execute(
                select(ClassTemplate).where(
                    ClassTemplate.academic_template_id == template.id,
                    ClassTemplate.level == "SECONDARY",
                )
            )

            if not secondary_classes.scalars().first():
                continue

            print(f"Updating {template.name}")

            for name in MISSING_SECONDARY_SUBJECTS:
                subject = await get_or_create_secondary_subject(
                    db,
                    template,
                    name,
                )

                await map_subject_to_secondary_classes(
                    db,
                    template,
                    subject,
                )

        await db.commit()

        print("Secondary subjects fixed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
