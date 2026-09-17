from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .build_image_workflow import BuildEvent


@dataclass(frozen=True)
class StoredBuildEvent:
    event_id: str
    outcome: str
    image_path: str | None
    diagnostic: str | None


class ImageArchive:
    def __init__(self, database_path: Path, image_directory: Path) -> None:
        self.database_path = database_path
        self.image_directory = image_directory
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.image_directory.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS build_events (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    image_path TEXT,
                    diagnostic TEXT
                )
                """
            )

    def find(self, event_id: str) -> StoredBuildEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT event_id, outcome, image_path, diagnostic "
                "FROM build_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return StoredBuildEvent(*row) if row else None

    def save_release(self, event: BuildEvent, filename: str) -> StoredBuildEvent:
        return self._insert(event.event_id, "released", filename, None)

    def save_diagnostic(self, event: BuildEvent, diagnostic: str) -> StoredBuildEvent:
        return self._insert(event.event_id, "diagnostic", None, diagnostic)

    def _insert(
        self,
        event_id: str,
        outcome: str,
        image_path: str | None,
        diagnostic: str | None,
    ) -> StoredBuildEvent:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO build_events VALUES (?, ?, ?, ?)",
                (event_id, outcome, image_path, diagnostic),
            )
        return StoredBuildEvent(event_id, outcome, image_path, diagnostic)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

