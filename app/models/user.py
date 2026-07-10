from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .refresh_token import RefreshToken

""" class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    ACCOUNTANT = "accountant" """


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"


class User(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "users"

    first_name = mapped_column(String(100))

    last_name = mapped_column(String(100))

    email = mapped_column(String(255), unique=True)

    username = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    access_token = mapped_column(Text)
    password_hash = mapped_column(Text)

    is_active = mapped_column(Boolean, default=True)

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    credential = relationship(
        "UserCredential",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    student_profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    teacher_profile = relationship(
        "TeacherProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    parent_profile = relationship(
        "ParentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    attendance_records = relationship(
        "AttendanceRecord",
        back_populates="student",
    )

    teacher_assignments = relationship(
        "TeacherClassSubject",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )

    enrollments = relationship(
        "StudentEnrollment",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    school = relationship(
        "School",
        back_populates="users",
    )
    class_assignments = relationship(
        "ClassTeacher",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "username",
            name="uq_school_username",
        ),
    )

    @property
    def school_name(self):
        return self.school.name if self.school else None

    @property
    def school_logo(self):
        return self.school.logo if self.school else None
