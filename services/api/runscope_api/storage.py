import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from runscope_api.config import Settings, get_settings


class ArtifactStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...


class LocalArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Artifact key escaped the storage root")
        return target

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        del content_type
        target = self._path(key)

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)


class S3ArtifactStore:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
        self._bucket_ready = True

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        def upload() -> None:
            self._ensure_bucket()
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(upload)

    async def get(self, key: str) -> bytes:
        def download() -> bytes:
            self._ensure_bucket()
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return bytes(response["Body"].read())

        return await asyncio.to_thread(download)


def build_artifact_store(settings: Settings) -> ArtifactStore:
    if settings.artifact_backend == "local":
        return LocalArtifactStore(settings.local_artifact_dir)
    if settings.artifact_backend == "s3":
        return S3ArtifactStore(
            settings.s3_endpoint_url,
            settings.s3_access_key,
            settings.s3_secret_key,
            settings.s3_bucket,
        )
    raise RuntimeError(f"Unsupported artifact backend: {settings.artifact_backend}")


async def get_artifact_store() -> AsyncIterator[ArtifactStore]:
    yield build_artifact_store(get_settings())
