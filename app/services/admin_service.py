import itertools
import re
import secrets
import string
import unicodedata
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School
from app.models.user import User, UserRole
from app.models.user_credentials import UserCredential
from app.repositories.admin_repository import AdminRepository
from app.repositories.school_repository import SchoolRepository
from app.utils.helper import hash_password

# =====================================================
# HELPERS
# =====================================================


def slugify(name: str) -> str:
    """
    Convert a school name into a clean, URL-safe slug.

    Examples:
        "Abia International School"
        -> "abia-international-school"

        "Amazing Grace Nursery/Primary School"
        -> "amazing-grace-nursery-primary-school"

        "St. Mary's Academy"
        -> "st-marys-academy"

        "Royal & Great School"
        -> "royal-great-school"

        "ABC   International School"
        -> "abc-international-school"
    """
    if not name:
        return ""

    # Normalize Unicode characters.
    value = unicodedata.normalize("NFKD", name)

    # Remove accents/diacritics.
    value = value.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase.
    value = value.lower().strip()

    # Convert slash, backslash and ampersand to spaces.
    value = re.sub(r"[/\\&]+", " ", value)

    # Remove apostrophes.
    value = value.replace("'", "")

    # Replace all remaining non-alphanumeric characters with spaces.
    value = re.sub(r"[^a-z0-9]+", " ", value)

    # Convert whitespace to single hyphens.
    value = re.sub(r"\s+", "-", value)

    # Remove leading/trailing hyphens.
    value = value.strip("-")

    return value


def generate_code() -> str:
    """
    Generate a short school code.

    Example:
        A3F91C
    """
    return secrets.token_hex(3).upper()


def generate_password(length: int = 12) -> str:
    """
    Generate a secure random password.

    Requirements:
    - lowercase
    - uppercase
    - number
    - special character
    """
    alphabet = string.ascii_letters + string.digits + "@#$%&*!"

    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))

        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "@#$%&*!" for c in password)
        ):
            return password


def get_school_letters(school_name: str) -> str:
    """
    Extract only alphabetic characters from the school name.

    Example:
        "Abia International School"
        -> "ABIAINTERNATIONALSCHOOL"
    """
    return "".join(
        character.upper() for character in school_name if character.isalpha()
    )


def generate_username_candidates(
    school_name: str,
) -> list[str]:
    """
    Generate 3-letter username prefixes from the school name.

    The first three letters are preferred.

    Example:
        Abia International School

        ABI
        AII
        AIS
        AIA
        AIN
        ABS
        ...

    Final username format:

        ABI-ADMIN
        AII-ADMIN
        AIS-ADMIN

    No numeric suffixes are used.
    """

    letters = get_school_letters(school_name)

    if len(letters) < 3:
        return []

    candidates: list[str] = []

    # ---------------------------------------------
    # FIRST PREFERENCE
    # ---------------------------------------------

    first_three = letters[:3]
    candidates.append(first_three)

    # ---------------------------------------------
    # OTHER COMBINATIONS
    # ---------------------------------------------

    for combination in itertools.combinations(letters, 3):
        candidate = "".join(combination)

        if candidate not in candidates:
            candidates.append(candidate)

    return candidates


# =====================================================
# ADMIN SERVICE
# =====================================================


class AdminService:
    def __init__(self):
        self.repo = AdminRepository()
        self.school_repo = SchoolRepository()

    # =================================================
    # INTERNAL HELPERS
    # =================================================

    async def _generate_unique_slug(
        self,
        db: AsyncSession,
        school_name: str,
    ) -> str:
        """
        Generate a unique school slug.

        Examples:
            abia-international-school
            abia-international-school-2
            abia-international-school-3

        """
        base = slugify(school_name)

        if not base:
            raise ValueError("School name cannot generate a valid slug.")

        slug = base
        counter = 2

        while await self.school_repo.get_by_slug(
            db,
            slug,
        ):
            slug = f"{base}-{counter}"
            counter += 1

        return slug

    async def _generate_unique_username(
        self,
        db: AsyncSession,
        school_name: str,
    ) -> str:
        """
        Generate a unique school admin username.

        Format:

            XXX-ADMIN

        Example:

            ABI-ADMIN
            AII-ADMIN
            AIS-ADMIN
        """

        candidates = generate_username_candidates(school_name)

        if not candidates:
            raise ValueError("School name must contain at least 3 letters.")

        for prefix in candidates:
            username = f"{prefix}-ADMIN"

            existing = await self.repo.get_user_by_username(
                db,
                username,
            )

            if not existing:
                return username

        raise ValueError(
            f"Unable to generate a unique admin username for school '{school_name}'."
        )

    # =================================================
    # GET SCHOOLS
    # =================================================

    async def get_schools(
        self,
        db: AsyncSession,
        search: str | None = None,
        state: str | None = None,
        location: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ):
        return await self.school_repo.get_schools(
            db=db,
            search=search,
            state=state,
            location=location,
            page=page,
            per_page=per_page,
        )

    # =================================================
    # CREATE ONE SCHOOL
    # =================================================

    async def create_school(
        self,
        db: AsyncSession,
        payload,
    ):
        """
        Create ONE school together with:

        1. School
        2. Primary School Admin
        3. UserCredential

        This is intentionally a single-school registration
        operation. No batch/bulk school creation is included.
        """

        generated_password = generate_password()

        try:
            # -----------------------------------------
            # UNIQUE SLUG
            # -----------------------------------------

            slug = await self._generate_unique_slug(
                db=db,
                school_name=payload.school_name,
            )

            # -----------------------------------------
            # SCHOOL CODE
            # -----------------------------------------

            code = generate_code()

            # -----------------------------------------
            # CREATE SCHOOL
            # -----------------------------------------

            school = School(
                name=payload.school_name,
                slug=slug,
                code=code,
                phone=payload.phone,
                email=payload.admin_email,
                website=payload.website or None,
                whatsapp_number=payload.whatsapp_number or None,
                state=payload.state,
                address=payload.address,
                description=payload.description or None,
                is_active=True,
            )

            db.add(school)

            # Make school.id available.
            await db.flush()

            # -----------------------------------------
            # UNIQUE ADMIN USERNAME
            # -----------------------------------------

            username = await self._generate_unique_username(
                db=db,
                school_name=payload.school_name,
            )

            # -----------------------------------------
            # CREATE PRIMARY SCHOOL ADMIN
            # -----------------------------------------

            admin = User(
                first_name=payload.admin_first_name,
                last_name=payload.admin_last_name,
                username=username,
                email=payload.admin_email,
                password_hash=hash_password(generated_password),
                role=UserRole.SCHOOL_ADMIN,
                school_id=school.id,
                profile_completed=True,
            )

            db.add(admin)

            # Make admin.id available.
            await db.flush()

            # -----------------------------------------
            # SAVE LOGIN CREDENTIALS
            # -----------------------------------------

            credential = UserCredential(
                school_id=school.id,
                user_id=admin.id,
                username=username,
                password=generated_password,
            )

            db.add(credential)

            # -----------------------------------------
            # COMMIT
            # -----------------------------------------

            await db.commit()

            # -----------------------------------------
            # REFRESH
            # -----------------------------------------

            await db.refresh(school)

            return {
                "school": school,
                "credentials": {
                    "username": username,
                    "password": generated_password,
                },
            }

        except Exception:
            await db.rollback()
            raise

    # =================================================
    # DISABLE SCHOOL
    # =================================================

    async def disable_school(
        self,
        db: AsyncSession,
        school_id,
    ):
        school = await self.school_repo.get_by_id(
            db,
            school_id,
        )

        if not school:
            return None

        school.is_active = False

        return await self.school_repo.save(
            db,
            school,
        )

    # =================================================
    # ENABLE SCHOOL
    # =================================================

    async def enable_school(
        self,
        db: AsyncSession,
        school_id,
    ):
        school = await self.school_repo.get_by_id(
            db,
            school_id,
        )

        if not school:
            return None

        school.is_active = True

        return await self.school_repo.save(
            db,
            school,
        )

    # =================================================
    # CREATE ADDITIONAL SCHOOL ADMIN
    # =================================================

    async def create_school_admin(
        self,
        db: AsyncSession,
        payload,
    ):
        """
        Create another SCHOOL_ADMIN for an existing school.
        """

        school = await self.school_repo.get_by_id(
            db,
            payload["school_id"],
        )

        if not school:
            return None

        password = generate_password()

        try:
            # -----------------------------------------
            # UNIQUE USERNAME
            # -----------------------------------------

            username = await self._generate_unique_username(
                db=db,
                school_name=school.name,
            )

            # -----------------------------------------
            # CREATE USER
            # -----------------------------------------

            user = User(
                first_name=payload["first_name"],
                last_name=payload["last_name"],
                username=username,
                email=payload["email"],
                password_hash=hash_password(password),
                role=UserRole.SCHOOL_ADMIN,
                school_id=school.id,
                profile_completed=True,
            )

            db.add(user)

            await db.flush()

            # -----------------------------------------
            # SAVE CREDENTIAL
            # -----------------------------------------

            credential = UserCredential(
                school_id=school.id,
                user_id=user.id,
                username=username,
                password=password,
            )

            db.add(credential)

            await db.commit()

            await db.refresh(user)

            return {
                "user": user,
                "credentials": {
                    "username": username,
                    "password": password,
                },
            }

        except Exception:
            await db.rollback()
            raise

    # =================================================
    # RESET SCHOOL ADMIN PASSWORD
    # =================================================

    async def reset_school_admin_password(
        self,
        db: AsyncSession,
        user_id,
    ):
        user = await self.repo.get_user(
            db,
            user_id,
        )

        if not user:
            return None

        password = generate_password()

        try:
            user.password_hash = hash_password(password)

            credential = await self.repo.get_user_credential(
                db,
                user.id,
            )

            if credential:
                credential.password = password
                credential.username = user.username

            await db.commit()

            return {
                "username": user.username,
                "password": password,
            }

        except Exception:
            await db.rollback()
            raise

    # =================================================
    # DELETE ADMIN
    # =================================================

    async def delete_admin(
        self,
        db: AsyncSession,
        user_id,
    ):
        user = await self.repo.get_user(
            db,
            user_id,
        )

        if not user:
            return None

        try:
            await self.repo.delete_user(
                db,
                user,
            )

            await db.commit()

            return True

        except Exception:
            await db.rollback()
            raise

    # =================================================
    # ASSIGN SCHOOL ADMIN
    # =================================================

    async def assign_school_admin(
        self,
        db: AsyncSession,
        user_id,
        school_id,
    ):
        user = await self.repo.get_user(
            db,
            user_id,
        )

        school = await self.school_repo.get_by_id(
            db,
            school_id,
        )

        if not user or not school:
            return None

        try:
            user.role = UserRole.SCHOOL_ADMIN
            user.school_id = school.id

            result = await self.repo.save_user(
                db,
                user,
            )

            await db.commit()

            return result

        except Exception:
            await db.rollback()
            raise

    # =================================================
    # REVOKE SCHOOL ADMIN
    # =================================================

    async def revoke_school_admin(
        self,
        db: AsyncSession,
        user_id,
    ):
        user = await self.repo.get_user(
            db,
            user_id,
        )

        if not user:
            return None

        if user.role != UserRole.SCHOOL_ADMIN:
            return user

        try:
            user.role = UserRole.TEACHER

            result = await self.repo.save_user(
                db,
                user,
            )

            await db.commit()

            return result

        except Exception:
            await db.rollback()
            raise

    # =================================================
    # DASHBOARD STATS
    # =================================================

    async def get_dashboard_stats(
        self,
        db: AsyncSession,
    ):
        schools = await self.repo.count_schools(db)
        users = await self.repo.count_users(db)
        admins = await self.repo.count_school_admins(db)

        return {
            "schools": schools,
            "users": users,
            "admins": admins,
        }

    # =================================================
    # GET ADMINS
    # =================================================

    async def get_admins(
        self,
        db: AsyncSession,
    ):
        return await self.repo.get_admins(db)

    # =================================================
    # UPDATE SCHOOL
    # =================================================

    async def update_school(
        self,
        db: AsyncSession,
        school_id,
        payload,
    ):
        """
        Update an existing school and ensure that it has.

        a valid primary SCHOOL_ADMIN and UserCredential.

        Behavior:

        1. Update school information.
        2. Find existing SCHOOL_ADMIN.
        3. If admin exists:
        - update admin profile
        - preserve username/password
        4. If admin exists but credential is missing:
        - create UserCredential
        - generate a new password
        5. If no SCHOOL_ADMIN exists:
        - create SCHOOL_ADMIN
        - generate username/password
        - create UserCredential
        6. Return school + credentials.

        Existing credentials are NEVER changed during
        a normal school update.
        """
        # =================================================
        # GET SCHOOL
        # =================================================

        school = await self.school_repo.get_by_id(
            db,
            school_id,
        )

        if not school:
            return None

        try:
            # =================================================
            # UPDATE SCHOOL INFORMATION
            # =================================================

            school = await self.school_repo.update(
                db,
                school,
                payload,
            )

            # =================================================
            # FIND PRIMARY SCHOOL ADMIN
            # =================================================

            admin = next(
                (user for user in school.users if user.role == UserRole.SCHOOL_ADMIN),
                None,
            )

            # =================================================
            # VARIABLES
            # =================================================

            username: str | None = None
            password: str | None = None

            # =================================================
            # CASE 1:
            # ADMIN ALREADY EXISTS
            # =================================================

            if admin:
                # ---------------------------------------------
                # UPDATE ADMIN PROFILE
                # ---------------------------------------------

                admin.first_name = payload.admin_first_name
                admin.last_name = payload.admin_last_name
                admin.email = payload.admin_email

                db.add(admin)

                await db.flush()

                # ---------------------------------------------
                # CHECK CREDENTIAL
                # ---------------------------------------------

                credential = admin.credential

                # ---------------------------------------------
                # ADMIN HAS CREDENTIAL
                # ---------------------------------------------

                if credential:
                    username = credential.username
                    password = credential.password

                # ---------------------------------------------
                # ADMIN HAS NO CREDENTIAL
                # CREATE ONE
                # ---------------------------------------------

                else:
                    username = admin.username

                    # If username somehow doesn't exist,
                    # generate one.
                    if not username:
                        username = await self._generate_unique_username(
                            db=db,
                            school_name=school.name,
                        )

                        admin.username = username

                        db.add(admin)

                        await db.flush()

                    # Generate a new password because
                    # there is no stored credential.
                    password = generate_password()

                    credential = UserCredential(
                        school_id=school.id,
                        user_id=admin.id,
                        username=username,
                        password=password,
                    )

                    db.add(credential)

                    await db.flush()

            # =================================================
            # CASE 2:
            # NO SCHOOL ADMIN EXISTS
            # CREATE ADMIN + CREDENTIALS
            # =================================================

            else:
                # ---------------------------------------------
                # GENERATE USERNAME
                # ---------------------------------------------

                username = await self._generate_unique_username(
                    db=db,
                    school_name=school.name,
                )

                # ---------------------------------------------
                # GENERATE PASSWORD
                # ---------------------------------------------

                password = generate_password()

                # ---------------------------------------------
                # CREATE SCHOOL ADMIN
                # ---------------------------------------------

                admin = User(
                    first_name=payload.admin_first_name,
                    last_name=payload.admin_last_name,
                    username=username,
                    email=payload.admin_email,
                    password_hash=hash_password(password),
                    role=UserRole.SCHOOL_ADMIN,
                    school_id=school.id,
                    profile_completed=True,
                )

                db.add(admin)

                await db.flush()

                # ---------------------------------------------
                # CREATE CREDENTIAL
                # ---------------------------------------------

                credential = UserCredential(
                    school_id=school.id,
                    user_id=admin.id,
                    username=username,
                    password=password,
                )

                db.add(credential)

                await db.flush()

                # ---------------------------------------------
                # ADD ADMIN TO SCHOOL RELATIONSHIP
                # ---------------------------------------------

                school.users.append(admin)

            # =================================================
            # COMMIT EVERYTHING
            # =================================================

            await db.commit()

            # =================================================
            # REFRESH SCHOOL
            # =================================================

            await db.refresh(school)

            # =================================================
            # RETURN
            # =================================================

            return {
                "school": school,
                "credentials": {
                    "username": username,
                    "password": password,
                },
            }

        except Exception:
            await db.rollback()
            raise

    async def import_schools_from_excel(
        self,
        db: AsyncSession,
        file,
    ):
        """
        Import schools and their primary school admins from Excel.

        Expected columns:

            School Name
            State
            Address / LGA
            Admin First Name
            Admin Last Name
            Phone Number
            Generated Email (placeholder)
            Source No. (optional)

        Each valid row creates:

            1. School
            2. Primary SCHOOL_ADMIN
            3. UserCredential

        Invalid rows are skipped and reported.

        IMPORTANT:
        Each Excel row uses its own SAVEPOINT so a failed row
        does not roll back previously successful rows.
        """

        # =================================================
        # READ EXCEL
        # =================================================

        contents = await file.read()

        try:
            workbook = load_workbook(
                filename=BytesIO(contents),
                data_only=True,
            )
        except Exception:
            raise ValueError("Invalid Excel file. Please upload a valid .xlsx file.")

        worksheet = workbook.active

        # =================================================
        # READ HEADERS
        # =================================================

        headers = []

        for cell in worksheet[1]:
            value = cell.value

            if value is None:
                headers.append("")
            else:
                headers.append(str(value).strip())

        header_map = {
            header.lower(): index for index, header in enumerate(headers) if header
        }

        required_columns = [
            "school name",
            "state",
            "address / lga",
            "admin first name",
            "admin last name",
            "phone number",
        ]

        missing_columns = [
            column for column in required_columns if column not in header_map
        ]

        if missing_columns:
            raise ValueError(
                "Missing required Excel columns: " + ", ".join(missing_columns)
            )

        # =================================================
        # HELPERS
        # =================================================

        def get_value(row, column_name):
            index = header_map.get(column_name.lower())

            if index is None:
                return None

            if index >= len(row):
                return None

            value = row[index]

            if value is None:
                return None

            value = str(value).strip()

            return value or None

        # =================================================
        # RESULTS
        # =================================================

        imported = []
        skipped = []

        processed_rows = 0

        # =================================================
        # PROCESS ROWS
        # =================================================

        for excel_row_number, row in enumerate(
            worksheet.iter_rows(
                min_row=2,
                values_only=True,
            ),
            start=2,
        ):
            # ---------------------------------------------
            # IGNORE COMPLETELY EMPTY ROWS
            # ---------------------------------------------

            if not any(value is not None and str(value).strip() for value in row):
                continue

            processed_rows += 1

            # ---------------------------------------------
            # READ VALUES
            # ---------------------------------------------

            school_name = get_value(
                row,
                "School Name",
            )

            state = get_value(
                row,
                "State",
            )

            address = get_value(
                row,
                "Address / LGA",
            )

            first_name = get_value(
                row,
                "Admin First Name",
            )

            last_name = get_value(
                row,
                "Admin Last Name",
            )

            phone = get_value(
                row,
                "Phone Number",
            )

            email = get_value(
                row,
                "Generated Email (placeholder)",
            )

            source_no = get_value(
                row,
                "Source No.",
            )

            # ---------------------------------------------
            # VALIDATE REQUIRED DATA
            # ---------------------------------------------

            missing = []

            if not school_name:
                missing.append("School Name")

            if not state:
                missing.append("State")

            if not address:
                missing.append("Address / LGA")

            if not first_name:
                missing.append("Admin First Name")

            if not last_name:
                missing.append("Admin Last Name")

            if not phone:
                missing.append("Phone Number")

            if missing:
                skipped.append(
                    {
                        "row": excel_row_number,
                        "source_no": source_no,
                        "school": school_name,
                        "reason": ("Missing required fields: " + ", ".join(missing)),
                    }
                )

                continue

            # ---------------------------------------------
            # GENERATE EMAIL
            # ---------------------------------------------

            if not email:
                email = (
                    f"{first_name.lower().strip()}."
                    f"{last_name.lower().strip()}"
                    "@schoolmail.example"
                )

            # ---------------------------------------------
            # CHECK EXISTING SCHOOL
            # ---------------------------------------------

            existing_school = await self.school_repo.get_by_name(
                db,
                school_name,
            )

            if existing_school:
                skipped.append(
                    {
                        "row": excel_row_number,
                        "source_no": source_no,
                        "school": school_name,
                        "reason": "School already exists.",
                    }
                )

                continue

            # =================================================
            # CREATE ROW SAVEPOINT
            # =================================================

            try:
                async with db.begin_nested():
                    # -----------------------------------------
                    # GENERATE UNIQUE SLUG
                    # -----------------------------------------

                    slug = await self._generate_unique_slug(
                        db=db,
                        school_name=school_name,
                    )

                    # -----------------------------------------
                    # GENERATE SCHOOL CODE
                    # -----------------------------------------

                    code = generate_code()

                    # -----------------------------------------
                    # CREATE SCHOOL
                    # -----------------------------------------

                    school = School(
                        name=school_name,
                        slug=slug,
                        code=code,
                        phone=phone,
                        email=email,
                        website=None,
                        whatsapp_number=None,
                        state=state,
                        address=address,
                        description=None,
                        is_active=True,
                    )

                    db.add(school)

                    await db.flush()

                    # -----------------------------------------
                    # GENERATE USERNAME
                    # -----------------------------------------

                    username = await self._generate_unique_username(
                        db=db,
                        school_name=school_name,
                    )

                    # -----------------------------------------
                    # GENERATE PASSWORD
                    # -----------------------------------------

                    password = generate_password()

                    # -----------------------------------------
                    # CREATE ADMIN
                    # -----------------------------------------

                    admin = User(
                        first_name=first_name,
                        last_name=last_name,
                        username=username,
                        email=email,
                        password_hash=hash_password(password),
                        role=UserRole.SCHOOL_ADMIN,
                        school_id=school.id,
                        profile_completed=True,
                    )

                    db.add(admin)

                    await db.flush()

                    # -----------------------------------------
                    # CREATE CREDENTIAL
                    # -----------------------------------------

                    credential = UserCredential(
                        school_id=school.id,
                        user_id=admin.id,
                        username=username,
                        password=password,
                    )

                    db.add(credential)

                    await db.flush()

                # =================================================
                # SAVEPOINT SUCCESSFUL
                # =================================================

                imported.append(
                    {
                        "row": excel_row_number,
                        "source_no": source_no,
                        "school": school_name,
                        "username": username,
                        "password": password,
                    }
                )

            except Exception as exc:
                # =================================================
                # ONLY THIS ROW IS ROLLED BACK
                # =================================================

                reason = str(exc)

                # Clean up ugly database errors
                if "duplicate key" in reason.lower():
                    reason = (
                        "Duplicate value detected. "
                        "The school, username, email, code, or another "
                        "unique field already exists."
                    )

                skipped.append(
                    {
                        "row": excel_row_number,
                        "source_no": source_no,
                        "school": school_name,
                        "reason": reason,
                    }
                )

                continue

        # =================================================
        # COMMIT ALL SUCCESSFUL ROWS
        # =================================================

        try:
            await db.commit()

        except Exception as exc:
            await db.rollback()

            raise ValueError(f"Failed to commit imported schools: {str(exc)}")

        # =================================================
        # SUMMARY
        # =================================================

        return {
            "total_rows": processed_rows,
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "imported": imported,
            "skipped": skipped,
        }
