"""Event-by-event replay engine for fixture CSVs and future iPhone parity."""

from __future__ import annotations

import csv
from itertools import chain
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any, Callable, Iterable, Mapping

from .ingestion import IngestionDecision, TripIngestor, TripSession


ALLOWED_SPEEDS = (1, 5, 10, 30, "instant")
FORBIDDEN_INFERENCE_FIELDS = frozenset(
    {
        "mode",
        "transport_mode",
        "ground_truth",
        "ground_truth_mode",
        "segment",
        "ground_truth_segment",
        "expected_mode",
        "label",
        "target",
    }
)


@dataclass(frozen=True)
class ReplayUpdate:
    index: int
    decision: IngestionDecision
    session: TripSession


@dataclass(frozen=True)
class ReplayResult:
    status: str
    updates: tuple[ReplayUpdate, ...]
    session: TripSession


def read_replay_csv(path: str | Path) -> list[dict[str, Any]]:
    """Read GPS rows and reject evaluation labels from production replay."""

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {field.strip() for field in (reader.fieldnames or []) if field}
        forbidden = sorted(fields & FORBIDDEN_INFERENCE_FIELDS)
        if forbidden:
            raise ValueError(
                "production GPS replay cannot contain evaluation fields: "
                + ", ".join(forbidden)
            )
        return [dict(row) for row in reader]


class ReplayEngine:
    def __init__(self, ingestor: TripIngestor | None = None, *, speed: int | str = "instant"):
        if speed not in ALLOWED_SPEEDS:
            raise ValueError(f"speed must be one of {ALLOWED_SPEEDS}")
        self.ingestor = ingestor or TripIngestor()
        self.speed = speed
        self._pause = Event()
        self._pause.set()
        self._stop = Event()

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    def stop(self) -> None:
        self._stop.set()
        self._pause.set()

    def stream(
        self,
        payloads: Iterable[Mapping[str, Any]],
        *,
        on_update: Callable[[ReplayUpdate], None] | None = None,
    ) -> ReplayResult:
        iterator = iter(payloads)
        try:
            first = next(iterator)
        except StopIteration:
            raise ValueError("replay requires at least one GPS event")
        trip_id = str(first.get("trip_id", ""))
        device_id = str(first.get("device_id", ""))
        session = self.ingestor.start_trip(trip_id, device_id)
        updates: list[ReplayUpdate] = []
        previous_timestamp = None
        for index, payload in enumerate(chain((first,), iterator)):
            if self._stop.is_set():
                break
            self._pause.wait()
            timestamp = _parse_timestamp(payload.get("timestamp"))
            if previous_timestamp is not None and timestamp is not None and self.speed != "instant":
                delay = max(0.0, (timestamp - previous_timestamp).total_seconds() / int(self.speed))
                if delay:
                    time.sleep(min(delay, 1.0))
            previous_timestamp = timestamp or previous_timestamp
            decision = self.ingestor.ingest(payload)
            update = ReplayUpdate(index=index, decision=decision, session=session)
            updates.append(update)
            if on_update is not None:
                on_update(update)
        status = "STOPPED" if self._stop.is_set() else "STREAMED"
        return ReplayResult(status=status, updates=tuple(updates), session=session)


def _parse_timestamp(value: object):
    from datetime import datetime

    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
