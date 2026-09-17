from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIError, RateLimitError
from pydantic import BaseModel, Field

from .build_image_workflow import BuildEvent, BuildImageWorkflow, InfraiImageGenerator
from .image_archive import ImageArchive


class BuildEventRequest(BaseModel):
    event_id: str = Field(min_length=1)
    project: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    revision: str = Field(min_length=7)
    environment: str = Field(min_length=1)
    status: Literal["succeeded", "failed"]
    summary: str = Field(min_length=1, max_length=240)


class BuildEventResponse(BaseModel):
    event_id: str
    outcome: Literal["released", "diagnostic"]
    image_path: str | None
    diagnostic: str | None


def create_service(data_directory: Path | None = None) -> FastAPI:
    root = data_directory or Path(os.environ.get("DEVTOOL_IMAGE_DIR", ".local"))
    archive = ImageArchive(root / "events.sqlite3", root / "images")
    generator = InfraiImageGenerator(os.environ["INFRAI_API_KEY"])
    workflow = BuildImageWorkflow(archive, generator)
    service = FastAPI(title="Release visual service")

    @service.post("/build-events", response_model=BuildEventResponse)
    def record_build(request: BuildEventRequest) -> BuildEventResponse:
        event = BuildEvent(**request.model_dump())
        try:
            stored = workflow.record(event)
        except RateLimitError as error:
            raise HTTPException(status_code=429, detail="Image generation is busy; retry later") from error
        except (APIConnectionError, APIError) as error:
            raise HTTPException(status_code=502, detail="Image generation request was not completed") from error
        return BuildEventResponse(**stored.__dict__)

    return service


app = create_service()

