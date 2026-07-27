import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

from runscope_api.config import get_settings


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


async def get_artifact_store() -> AsyncIterator[ArtifactStore]:
    settings = get_settings()
    if settings.artifact_backend != "local":
        raise RuntimeError(f"Unsupported artifact backend: {settings.artifact_backend}")
    yield LocalArtifactStore(settings.local_artifact_dir)
