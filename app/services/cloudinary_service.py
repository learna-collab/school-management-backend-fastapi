from uuid import UUID

import cloudinary.uploader
from fastapi import HTTPException, UploadFile

# ensure cloudinary is configured
from app.main import cloudinary as cloudinary_config  # noqa: F401


class CloudinaryService:
    async def upload_file(
        self,
        *,
        file: UploadFile,
        folder: str,
        public_id: str | None = None,
        resource_type: str = "auto",
    ) -> str:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid file.")

        contents = await file.read()

        try:
            result = cloudinary.uploader.upload(
                contents,
                folder=folder,
                public_id=public_id,
                overwrite=True,
                resource_type=resource_type,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Cloudinary upload failed: {str(e)}",
            ) from e

        return result["secure_url"]

    async def upload_bytes(
        self,
        *,
        contents: bytes,
        filename: str,
        folder: str,
        public_id: str | None = None,
        resource_type: str = "auto",
    ) -> str:
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type=resource_type,
        )

        return result["secure_url"]


cloudinary_service = CloudinaryService()
