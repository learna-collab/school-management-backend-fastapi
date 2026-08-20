from typing import Any

import cloudinary.uploader
from fastapi import HTTPException, UploadFile


class CloudinaryService:
    async def upload_file(
        self,
        *,
        file: UploadFile,
        folder: str,
        public_id: str | None = None,
        resource_type: str = "auto",
    ) -> dict[str, Any]:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid file.",
            )

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

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
        }

    async def upload_bytes(
        self,
        *,
        contents: bytes,
        filename: str,
        folder: str,
        public_id: str | None = None,
        resource_type: str = "auto",
    ) -> dict[str, Any]:
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

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
        }

    async def delete_file(
        self,
        *,
        public_id: str,
        resource_type: str = "image",
    ) -> bool:
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
            )

            return result.get("result") in {
                "ok",
                "not found",
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Cloudinary delete failed: {str(e)}",
            ) from e


cloudinary_service = CloudinaryService()
