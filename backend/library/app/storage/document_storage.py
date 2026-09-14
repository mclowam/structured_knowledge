from app.core.config import Config, session_minio


class DocumentStorage:
    def __init__(self, settings: Config):
        self._settings = settings

    async def upload_document(
            self,
            file_obj,
            key: str,
            content_type: str | None = None,
    ):
        extra: dict[str, str] = {}
        if content_type:
            extra["ContentType"] = content_type

        async with session_minio.client(
                "s3",
                endpoint_url=self._settings.MINIO_ENDPOINT,
                aws_access_key_id=self._settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=self._settings.MINIO_SECRET_KEY,
        ) as s3:
            bucket = self._settings.MINIO_BUCKET
            if extra:
                await s3.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra)
            else:
                await s3.upload_fileobj(file_obj, bucket, key)

    async def get_bytes(self, key: str) -> tuple[bytes, str]:
        async with session_minio.client(
                "s3",
                endpoint_url=self._settings.MINIO_ENDPOINT,
                aws_access_key_id=self._settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=self._settings.MINIO_SECRET_KEY,
        ) as s3:
            response = await s3.get_object(
                Bucket=self._settings.MINIO_BUCKET,
                Key=key,
            )
            data = await response["Body"].read()

            content_type = response.get("ContentType", "application/octet-stream")

            return data, content_type

    async def delete_object(self, key: str):
        async with session_minio.client(
                "s3",
                endpoint_url=self._settings.MINIO_ENDPOINT,
                aws_access_key_id=self._settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=self._settings.MINIO_SECRET_KEY,
        ) as s3:
            await s3.delete_object(
                Bucket=self._settings.MINIO_BUCKET,
                Key=key,
            )