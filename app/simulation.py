from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple

from .database import Database
from .models import Aquarium, Fish, Task


class SimulationEngine:
    def __init__(self, database: Database) -> None:
        self._database = database
        self._aquariums: List[Aquarium] = []
        self._fish: Dict[int, List[Fish]] = {}
        self._tasks: Dict[int, List[Task]] = {}
        self._last_tick = datetime.now(timezone.utc)
        self.reload()

    def reload(self) -> None:
        self._aquariums = self._database.aquariums()
        self._fish = {
            aquarium.id: self._database.fish_for_aquarium(aquarium.id)
            for aquarium in self._aquariums
            if aquarium.id is not None
        }
        self._tasks = {
            aquarium.id: self._database.tasks_for_aquarium(aquarium.id)
            for aquarium in self._aquariums
            if aquarium.id is not None
        }
        self._last_tick = datetime.now(timezone.utc)

    def aquariums(self) -> List[Aquarium]:
        return self._aquariums

    def fish_for(self, aquarium_id: int) -> List[Fish]:
        return self._fish.get(aquarium_id, [])

    def tasks_for(self, aquarium_id: int) -> List[Task]:
        return self._tasks.get(aquarium_id, [])

    def tick(self) -> None:
        now = datetime.now(timezone.utc)
        elapsed = now - self._last_tick
        if elapsed <= timedelta(0):
            return
        minutes = elapsed.total_seconds() / 60.0
        for aquarium in self._aquariums:
            if aquarium.id is None:
                continue
            adjustment_ratio = 1.0 - math.exp(-minutes / 18.0)
            aquarium.current_temperature += (aquarium.target_temperature - aquarium.current_temperature) * adjustment_ratio
            aquarium.cleanliness = max(0.0, aquarium.cleanliness - minutes * 0.18)
            fishes = self._fish.get(aquarium.id, [])
            for fish in fishes:
                fish.hunger = min(100.0, fish.hunger + minutes * 0.45)
                penalty = 0.0
                if fish.hunger > 70.0:
                    penalty += (fish.hunger - 70.0) * 0.02 * minutes
                temperature_gap = abs(aquarium.current_temperature - aquarium.target_temperature)
                if temperature_gap > 2.5:
                    penalty += (temperature_gap - 2.5) * 0.5 * minutes
                if aquarium.cleanliness < 40.0:
                    penalty += (40.0 - aquarium.cleanliness) * 0.01 * minutes
                fish.health = max(10.0, min(100.0, fish.health - penalty))
            self._database.update_fish(fishes)
            self._database.upsert_aquarium(aquarium)
        self._last_tick = now

    def feed_fish(self, aquarium_id: int) -> None:
        fishes = self._fish.get(aquarium_id, [])
        updated: List[Fish] = []
        for fish in fishes:
            fish.hunger = max(0.0, fish.hunger - 45.0)
            fish.health = min(100.0, fish.health + 8.0)
            updated.append(fish)
        if updated:
            self._database.update_fish(updated)
            self._fish[aquarium_id] = updated

    def clean_aquarium(self, aquarium_id: int) -> None:
        for aquarium in self._aquariums:
            if aquarium.id == aquarium_id:
                timestamp = datetime.now(timezone.utc)
                aquarium.cleanliness = 100.0
                aquarium.last_cleaned_at = timestamp
                self._database.set_aquarium_cleaned(aquarium_id, timestamp)
                break

    def adjust_temperature(self, aquarium_id: int, target_temperature: float) -> None:
        for aquarium in self._aquariums:
            if aquarium.id == aquarium_id:
                aquarium.target_temperature = target_temperature
                self._database.upsert_aquarium(aquarium)
                break

    def delete_aquarium(self, aquarium_id: int) -> None:
        self._database.delete_aquarium(aquarium_id)
        self.reload()

    def register_temperature(self, aquarium_id: int, current_temperature: float) -> None:
        for aquarium in self._aquariums:
            if aquarium.id == aquarium_id:
                aquarium.current_temperature = current_temperature
                self._database.upsert_aquarium(aquarium)
                break

    def create_aquarium(self, name: str, target_temperature: float) -> Aquarium:
        now = datetime.now(timezone.utc)
        aquarium = Aquarium(
            id=None,
            name=name,
            target_temperature=target_temperature,
            current_temperature=target_temperature,
            cleanliness=90.0,
            last_cleaned_at=now,
        )
        stored = self._database.upsert_aquarium(aquarium)
        if stored.id is None:
            raise RuntimeError("Falha ao criar aquário")
        self._aquariums.append(stored)
        self._fish[stored.id] = []
        self._tasks[stored.id] = []
        return stored

    def create_fish(self, aquarium_id: int, name: str, species: str) -> Fish:
        now = datetime.now(timezone.utc)
        fish = Fish(
            id=None,
            aquarium_id=aquarium_id,
            name=name,
            species=species,
            hunger=35.0,
            health=95.0,
            created_at=now,
        )
        stored = self._database.insert_fish(fish)
        fishes = self._fish.get(aquarium_id)
        if fishes is None:
            fishes = []
            self._fish[aquarium_id] = fishes
        fishes.append(stored)
        return stored

    def remove_fish(self, fish_id: int, aquarium_id: int) -> None:
        fishes = self._fish.get(aquarium_id, [])
        self._fish[aquarium_id] = [fish for fish in fishes if fish.id != fish_id]
        self._database.delete_fish(fish_id)

    def add_task(self, aquarium_id: int, kind: str, interval_minutes: int) -> Task:
        now = datetime.now(timezone.utc)
        task = Task(id=None, aquarium_id=aquarium_id, kind=kind, interval_minutes=interval_minutes, last_run_at=now - timedelta(minutes=interval_minutes))
        stored = self._database.upsert_task(task)
        tasks = self._tasks.get(aquarium_id)
        if tasks is None:
            tasks = []
            self._tasks[aquarium_id] = tasks
        tasks.append(stored)
        return stored

    def due_tasks(self) -> List[Tuple[Task, Aquarium]]:
        now = datetime.now(timezone.utc)
        pending: List[Tuple[Task, Aquarium]] = []
        for aquarium in self._aquariums:
            if aquarium.id is None:
                continue
            tasks = self._tasks.get(aquarium.id, [])
            for task in tasks:
                threshold = task.last_run_at + timedelta(minutes=task.interval_minutes)
                if now >= threshold:
                    pending.append((task, aquarium))
        return pending

    def mark_task_done(self, task: Task) -> None:
        now = datetime.now(timezone.utc)
        if task.id is None:
            stored = self._database.upsert_task(task)
            task.id = stored.id
        task.last_run_at = now
        if task.id is not None:
            self._database.update_task_timestamp(task.id, now)

    def export_snapshot(self) -> Dict[str, object]:
        return {
            "aquariums": [
                {
                    "id": aquarium.id,
                    "name": aquarium.name,
                    "target_temperature": aquarium.target_temperature,
                    "current_temperature": aquarium.current_temperature,
                    "cleanliness": aquarium.cleanliness,
                    "last_cleaned_at": aquarium.last_cleaned_at.isoformat(),
                }
                for aquarium in self._aquariums
            ],
            "fish": [
                {
                    "id": fish.id,
                    "aquarium_id": fish.aquarium_id,
                    "name": fish.name,
                    "species": fish.species,
                    "hunger": fish.hunger,
                    "health": fish.health,
                    "created_at": fish.created_at.isoformat(),
                }
                for fishes in self._fish.values()
                for fish in fishes
            ],
            "tasks": [
                {
                    "id": task.id,
                    "aquarium_id": task.aquarium_id,
                    "kind": task.kind,
                    "interval_minutes": task.interval_minutes,
                    "last_run_at": task.last_run_at.isoformat(),
                }
                for tasks in self._tasks.values()
                for task in tasks
            ],
        }


