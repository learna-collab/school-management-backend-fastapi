import asyncio
import re

from sqlalchemy import text

from app.db.database import async_session_local

# ============================================================
# SLUGIFY
# ============================================================


def slugify(name: str) -> str:
    """
    Convert a school name into a URL-safe slug.

    Examples:

        Amazing Grace Nursery/Primary School
        ->
        amazing-grace-nursery-primary-school

        St. Mary's School
        ->
        st-marys-school
    """

    if not name:
        return ""

    name = name.lower().strip()

    # Replace anything that is not a letter or number
    # with a hyphen.
    name = re.sub(r"[^a-z0-9]+", "-", name)

    # Remove duplicate hyphens.
    name = re.sub(r"-+", "-", name)

    # Remove leading/trailing hyphens.
    return name.strip("-")


# ============================================================
# FIX EXISTING SCHOOL SLUGS
# ============================================================


async def fix_existing_school_slugs():
    async with async_session_local() as db:
        try:
            # ------------------------------------------------
            # IMPORTANT:
            # Use raw SQL instead of select(School).
            #
            # This avoids SQLAlchemy initializing the School
            # ORM mapper and hitting the AdmissionEnquiry
            # relationship error.
            # ------------------------------------------------

            result = await db.execute(
                text("""
                    SELECT id, name, slug
                    FROM schools
                    ORDER BY id
                """)
            )

            schools = result.fetchall()

            if not schools:
                print("No schools found.")
                return

            print(f"Found {len(schools)} schools.")
            print("Checking school slugs...\n")

            # ------------------------------------------------
            # Keep track of slugs already used.
            #
            # This prevents two schools from ending up with
            # the same slug.
            # ------------------------------------------------

            used_slugs = set()

            # First collect all existing slugs that we are NOT
            # changing. This allows the new slugs to avoid
            # collisions with them.

            for school_id, name, slug in schools:
                if slug and "/" not in slug:
                    used_slugs.add(slug)

            updated_count = 0
            skipped_count = 0

            # ------------------------------------------------
            # PROCESS SCHOOLS
            # ------------------------------------------------

            for school_id, name, old_slug in schools:
                if not name:
                    print(f"[SKIPPED] ID {school_id}: School has no name.")
                    skipped_count += 1
                    continue

                new_slug = slugify(name)

                if not new_slug:
                    print(
                        f"[SKIPPED] ID {school_id}: "
                        f"Unable to generate slug from '{name}'."
                    )
                    skipped_count += 1
                    continue

                # ------------------------------------------------
                # If the generated slug already exists, create:
                #
                # school-name-2
                # school-name-3
                # ...
                # ------------------------------------------------

                base_slug = new_slug
                counter = 2

                while new_slug in used_slugs:
                    # If this is already the school's current slug,
                    # don't generate another suffix.
                    if old_slug == new_slug:
                        break

                    new_slug = f"{base_slug}-{counter}"
                    counter += 1

                # ------------------------------------------------
                # No change required
                # ------------------------------------------------

                if old_slug == new_slug:
                    skipped_count += 1
                    continue

                # ------------------------------------------------
                # Update directly in database
                # ------------------------------------------------

                await db.execute(
                    text("""
                        UPDATE schools
                        SET slug = :new_slug
                        WHERE id = :school_id
                    """),
                    {
                        "new_slug": new_slug,
                        "school_id": school_id,
                    },
                )

                used_slugs.add(new_slug)

                updated_count += 1

                print(
                    f"[UPDATED] {name}\n"
                    f"          OLD: {old_slug}\n"
                    f"          NEW: {new_slug}\n"
                )

            # ------------------------------------------------
            # COMMIT
            # ------------------------------------------------

            await db.commit()

            print("=" * 60)
            print("SLUG MIGRATION COMPLETE")
            print("=" * 60)
            print(f"Total schools : {len(schools)}")
            print(f"Updated       : {updated_count}")
            print(f"Skipped       : {skipped_count}")
            print("=" * 60)

        except Exception as exc:
            await db.rollback()

            print("\nSLUG MIGRATION FAILED")
            print(f"Error: {exc}")

            raise


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    asyncio.run(fix_existing_school_slugs())
