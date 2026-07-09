from fastapi import APIRouter

from . import (
    academic,
    admin,
    admin_registration,
    auth,
    blog,
    class_setup_router,
    profile,
    school_admin,
    students,
    teacher,
    user,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(students.router)
api_router.include_router(teacher.router)
api_router.include_router(profile.router)
api_router.include_router(admin.router)
api_router.include_router(school_admin.router)
api_router.include_router(blog.router)
api_router.include_router(academic.router)
api_router.include_router(admin_registration.router)
api_router.include_router(class_setup_router.router)
