from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Aquarium:
    id: Optional[int]
    name: str
    target_temperature: float
    current_temperature: float
    cleanliness: float
    last_cleaned_at: datetime


@dataclass(slots=True)
class Fish:
    id: Optional[int]
    aquarium_id: int
    name: str
    species: str
    hunger: float
    health: float
    created_at: datetime


@dataclass(slots=True)
class Task:
    id: Optional[int]
    aquarium_id: int
    kind: str
    interval_minutes: int
    last_run_at: datetime

