from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.services.cloudinary_service import cloudinary_service

MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
    ".zip",
}


class BlogAttachmentUploadService:
    async def upload(self, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Please select a file.",
            )

        filename = Path(file.filename).name.strip()
        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="This document format is not supported.",
            )

        try:
            contents = await file.read(MAX_ATTACHMENT_SIZE + 1)

            if not contents:
                raise HTTPException(
                    status_code=400,
                    detail="The selected file is empty.",
                )

            if len(contents) > MAX_ATTACHMENT_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="Maximum attachment size is 20 MB.",
                )

            uploaded = await cloudinary_service.upload_bytes(
                contents=contents,
                filename=filename,
                folder="lerna/blog-attachments",
                public_id=uuid4().hex,
                resource_type="raw",
            )

            return {
                "filename": filename,
                "url": uploaded["url"],
                "public_id": uploaded["public_id"],
                "content_type": file.content_type,
                "file_size": len(contents),
            }

        finally:
            await file.close()


blog_attachment_upload_service = BlogAttachmentUploadService()
