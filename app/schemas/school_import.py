from pydantic import BaseModel, EmailStr


class SchoolImportRow(BaseModel):
    school_name: str
    phone: str
    whatsapp_number: str | None = None
    state: str
    address: str
    website: str | None = None
    description: str | None = None

    admin_first_name: str
    admin_last_name: str
    admin_email: EmailStr


class SchoolImportError(BaseModel):
    row: int
    errors: list[str]


class SchoolImportResult(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[SchoolImportError]
