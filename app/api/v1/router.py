from fastapi import APIRouter

from app.api.v1.marketplace.admin import router as marketplace_admin_router
from app.api.v1.marketplace.public import router as marketplace_public_router
from app.api.v1.marketplace.vendor import router as marketplace_vendor_router

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
from .directory.admission_enquiries import router as admission_enquires_router
from .directory.admissions import router as admission_router
from .directory.directory_school import router as directory_school_router
from .directory.facilities import router as facilities_router
from .directory.gallery import router as gallery_router
from .directory.locations import router as locations_router
from .directory.programs import router as programs_router
from .school_admin import academic_period, school_admin
from .school_admin import lessons as school_admin_lessons
from .school_admin.school_admin_directory import router as school_admin_directory_router
from .super_admin import academic as super_admin_academic
from .super_admin import lessons as super_admin_lessons
from .super_admin.admin_directory import router as admin_directory_router
from .teacher import lessons as teacher_lessons
from .teacher import teacher

api_router = APIRouter()
api_router.include_router(locations_router)
api_router.include_router(admission_enquires_router)
api_router.include_router(admission_router)
api_router.include_router(facilities_router)
api_router.include_router(gallery_router)
api_router.include_router(programs_router)
api_router.include_router(school_admin_directory_router)
api_router.include_router(admin_directory_router)
api_router.include_router(super_admin_lessons.router)
api_router.include_router(directory_school_router)
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

api_router.include_router(marketplace_admin_router)
api_router.include_router(marketplace_vendor_router)

api_router.include_router(marketplace_public_router)
