from pathlib import Path

from devtool_images.build_image_workflow import BuildEvent, BuildImageWorkflow
from devtool_images.image_archive import ImageArchive


class RecordingGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, event: BuildEvent, destination: Path) -> None:
        self.calls += 1
        destination.write_bytes(b"generated-image")


def test_successful_build_is_released_once(tmp_path: Path) -> None:
    generator = RecordingGenerator()
    archive = ImageArchive(tmp_path / "events.sqlite3", tmp_path / "images")
    workflow = BuildImageWorkflow(archive, generator)
    event = BuildEvent(
        event_id="build-42",
        project="docs-site",
        revision="abc123def456",
        environment="preview",
        status="succeeded",
        summary="Adds searchable API reference pages",
    )

    first = workflow.record(event)
    replay = workflow.record(event)

    assert first.outcome == "released"
    assert first == replay
    assert generator.calls == 1
    assert (archive.image_directory / first.image_path).read_bytes() == b"generated-image"


def test_failed_build_becomes_diagnostic_without_an_image(tmp_path: Path) -> None:
    generator = RecordingGenerator()
    archive = ImageArchive(tmp_path / "events.sqlite3", tmp_path / "images")
    workflow = BuildImageWorkflow(archive, generator)
    event = BuildEvent(
        event_id="build-43",
        project="dashboard",
        revision="def456abc123",
        environment="production",
        status="failed",
        summary="Type check failed in the release route",
    )

    stored = workflow.record(event)

    assert stored.outcome == "diagnostic"
    assert stored.image_path is None
    assert stored.diagnostic == "dashboard@def456ab: Type check failed in the release route"
    assert generator.calls == 0

