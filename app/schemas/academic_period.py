from uuid import UUID

from pydantic import BaseModel


class SimpleSessionResponse(BaseModel):
    id: UUID
    name: str


class SimpleTermResponse(BaseModel):
    id: UUID
    name: str


class AcademicPeriodOptionsResponse(BaseModel):
    sessions: list[SimpleSessionResponse]
    terms: list[SimpleTermResponse]


class SchoolAcademicPeriodResponse(BaseModel):
    session_id: UUID
    session_name: str
    term_id: UUID
    term_name: str


class UpdateSchoolAcademicPeriodRequest(BaseModel):
    session_id: UUID
    term_id: UUID
