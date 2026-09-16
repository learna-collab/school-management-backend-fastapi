import asyncio

from sqlalchemy import select

from app.db.database import async_session_local
from app.models.academic_template import AcademicTemplate
from app.models.class_template import ClassTemplate

EXPECTED = {
    "Nursery & Primary": 9,
    "Secondary": 6,
    "Primary": 6,
    "Nursery, Primary & Secondary": 15,
}


async def main():
    async with async_session_local() as db:
        result = await db.execute(
            select(AcademicTemplate).order_by(AcademicTemplate.name)
        )

        templates = result.scalars().all()

        print("\n==============================")
        print("ACADEMIC TEMPLATE DIAGNOSTIC")
        print("==============================\n")

        if not templates:
            print("NO ACADEMIC TEMPLATES FOUND.")
            return

        for template in templates:
            result = await db.execute(
                select(ClassTemplate)
                .where(ClassTemplate.academic_template_id == template.id)
                .order_by(
                    ClassTemplate.sort_order,
                    ClassTemplate.name,
                )
            )

            classes = result.scalars().all()

            expected = EXPECTED.get(template.name)

            print(f"Template: {template.name}")
            print(f"ID:       {template.id}")
            print(f"Expected: {expected}")
            print(f"Actual:   {len(classes)}")
            print()

            for school_class in classes:
                print(
                    f"  {school_class.sort_order:>2}. "
                    f"{school_class.name:<15} "
                    f"level={school_class.level}"
                )

            if expected is not None:
                if len(classes) == expected:
                    print("STATUS:   OK")
                else:
                    print("STATUS:   WRONG COUNT")

            print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
