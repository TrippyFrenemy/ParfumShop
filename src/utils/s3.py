import uuid
import mimetypes
from contextlib import asynccontextmanager

from aiobotocore.session import get_session
from fastapi import UploadFile, HTTPException

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


class S3Client:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str,
        region: str = "",
        public_url: str = "",
    ):
        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        if region:
            self.config["region_name"] = region
        self.bucket_name = bucket_name
        self.public_url = public_url.rstrip("/")
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client("s3", **self.config) as client:
            yield client

    def _get_public_url(self, key: str) -> str:
        return f"{self.public_url}/{key}"

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        async with self.get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        return self._get_public_url(key)

    async def upload_product_image(
        self,
        file_data: bytes,
        product_id: int,
        original_filename: str,
    ) -> str:
        ext = original_filename.rsplit(".", 1)[-1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        key = f"images/products/{product_id}/{unique_name}"
        content_type = mimetypes.guess_type(original_filename)[0] or "image/jpeg"
        return await self.upload_bytes(file_data, key, content_type)

    async def upload_category_image(
        self,
        file_data: bytes,
        category_id: int,
        original_filename: str,
    ) -> str:
        ext = original_filename.rsplit(".", 1)[-1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        key = f"images/categories/{category_id}/{unique_name}"
        content_type = mimetypes.guess_type(original_filename)[0] or "image/jpeg"
        return await self.upload_bytes(file_data, key, content_type)

    async def delete_file(self, key: str) -> None:
        async with self.get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=key)

    async def delete_by_url(self, url: str) -> None:
        if url and url.startswith(self.public_url):
            key = url[len(self.public_url) :].lstrip("/")
            await self.delete_file(key)

    async def delete_by_prefix(self, prefix: str) -> None:
        async with self.get_client() as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(
                Bucket=self.bucket_name, Prefix=prefix
            ):
                objects = page.get("Contents", [])
                if objects:
                    await client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
                    )


async def validate_image_upload(file: UploadFile) -> bytes:
    if not file.filename:
        raise HTTPException(400, "Файл не выбран")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            400,
            f"Тип файла '.{ext}' не поддерживается. "
            f"Допустимые: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            400,
            f"Файл слишком большой ({len(data) // 1024}КБ). "
            f"Максимум: {MAX_IMAGE_SIZE // 1024 // 1024}МБ",
        )

    return data


_s3_client: S3Client | None = None


def get_s3_client() -> S3Client:
    global _s3_client
    if _s3_client is None:
        from src.config import settings

        if not settings.S3_ACCESS_KEY:
            raise RuntimeError(
                "S3 не настроен. Укажите S3_ACCESS_KEY и другие S3_ переменные в .env"
            )
        _s3_client = S3Client(
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            bucket_name=settings.S3_BUCKET_NAME,
            region=settings.S3_REGION,
            public_url=settings.S3_PUBLIC_URL,
        )
    return _s3_client
