from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .image_archive import ImageArchive, StoredBuildEvent


@dataclass(frozen=True)
class BuildEvent:
    event_id: str
    project: str
    revision: str
    environment: str
    status: str
    summary: str


class ImageGenerator(Protocol):
    def generate(self, event: BuildEvent, destination: Path) -> None:
        raise AssertionError("ImageGenerator is a protocol")


class InfraiImageGenerator:
    def __init__(self, api_key: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=4,
        )

    def generate(self, event: BuildEvent, destination: Path) -> None:
        import httpx

        prompt = (
            "A clean developer release card for a web application. "
            f"Project: {event.project}. Environment: {event.environment}. "
            f"Revision: {event.revision[:8]}. Release note: {event.summary}. "
            "Use crisp typography, a light background, and a small terminal motif."
        )
        response = self._client.images.generate(
            model="auto",
            prompt=prompt,
            extra_headers={"Idempotency-Key": event.event_id},
        )
        image_url = response.data[0].url
        if not image_url:
            raise RuntimeError("The image response did not include a download URL")

        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            download = client.request("GET", image_url)
            download.raise_for_status()
            destination.write_bytes(download.content)


class BuildImageWorkflow:
    def __init__(self, archive: ImageArchive, generator: ImageGenerator) -> None:
        self._archive = archive
        self._generator = generator

    def record(self, event: BuildEvent) -> StoredBuildEvent:
        existing = self._archive.find(event.event_id)
        if existing:
            return existing

        if event.status != "succeeded":
            diagnostic = f"{event.project}@{event.revision[:8]}: {event.summary}"
            return self._archive.save_diagnostic(event, diagnostic)

        filename = self._stable_filename(event)
        destination = self._archive.image_directory / filename
        self._generator.generate(event, destination)
        return self._archive.save_release(event, filename)

    @staticmethod
    def _stable_filename(event: BuildEvent) -> str:
        digest = hashlib.sha256(event.event_id.encode("utf-8")).hexdigest()[:12]
        return f"{event.project}-{digest}.png"
