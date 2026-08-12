from fastapi import APIRouter

from . import (
    admin,
    admin_registration,
    admin_setting,
    auth,
    blog,
    cbt,
    cbt_batch_upload,
    class_setup_router,
    profile,
    students,
    user,
)
from .school_admin import academic_period, school_admin
from .school_admin import lessons as school_admin_lessons
from .super_admin import academic as super_admin_academic
from .super_admin import lessons as super_admin_lessons
from .teacher import lessons as teacher_lessons
from .teacher import teacher

api_router = APIRouter()
api_router.include_router(super_admin_lessons.router)
api_router.include_router(super_admin_academic.router)
api_router.include_router(academic_period.router)
api_router.include_router(school_admin_lessons.router)
api_router.include_router(teacher_lessons.router)
api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(students.router)
api_router.include_router(teacher.router)
api_router.include_router(profile.router)
api_router.include_router(admin.router)
api_router.include_router(school_admin.router)
api_router.include_router(admin_setting.router)
api_router.include_router(blog.router)

api_router.include_router(admin_registration.router)
api_router.include_router(class_setup_router.router)
api_router.include_router(cbt.router)
api_router.include_router(cbt_batch_upload.router)
