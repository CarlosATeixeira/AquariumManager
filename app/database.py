from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import Aquarium, Fish, Task


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._configure()
        self._initialize()

    def _configure(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS aquariums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_temperature REAL NOT NULL,
                current_temperature REAL NOT NULL,
                cleanliness REAL NOT NULL,
                last_cleaned_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fish (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aquarium_id INTEGER NOT NULL REFERENCES aquariums(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                hunger REAL NOT NULL,
                health REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aquarium_id INTEGER NOT NULL REFERENCES aquariums(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                last_run_at TEXT NOT NULL
            );
            """
        )
        self._connection.commit()

    def aquariums(self) -> list[Aquarium]:
        rows = self._connection.execute(
            "SELECT id, name, target_temperature, current_temperature, cleanliness, last_cleaned_at FROM aquariums ORDER BY id"
        ).fetchall()
        return [
            Aquarium(
                id=row["id"],
                name=row["name"],
                target_temperature=row["target_temperature"],
                current_temperature=row["current_temperature"],
                cleanliness=row["cleanliness"],
                last_cleaned_at=datetime.fromisoformat(row["last_cleaned_at"]),
            )
            for row in rows
        ]

    def upsert_aquarium(self, aquarium: Aquarium) -> Aquarium:
        if aquarium.id is None:
            cursor = self._connection.execute(
                "INSERT INTO aquariums (name, target_temperature, current_temperature, cleanliness, last_cleaned_at) VALUES (?, ?, ?, ?, ?)",
                (
                    aquarium.name,
                    aquarium.target_temperature,
                    aquarium.current_temperature,
                    aquarium.cleanliness,
                    aquarium.last_cleaned_at.isoformat(),
                ),
            )
            self._connection.commit()
            return Aquarium(
                id=cursor.lastrowid,
                name=aquarium.name,
                target_temperature=aquarium.target_temperature,
                current_temperature=aquarium.current_temperature,
                cleanliness=aquarium.cleanliness,
                last_cleaned_at=aquarium.last_cleaned_at,
            )
        self._connection.execute(
            "UPDATE aquariums SET name = ?, target_temperature = ?, current_temperature = ?, cleanliness = ?, last_cleaned_at = ? WHERE id = ?",
            (
                aquarium.name,
                aquarium.target_temperature,
                aquarium.current_temperature,
                aquarium.cleanliness,
                aquarium.last_cleaned_at.isoformat(),
                aquarium.id,
            ),
        )
        self._connection.commit()
        return aquarium

    def fish_for_aquarium(self, aquarium_id: int) -> list[Fish]:
        rows = self._connection.execute(
            "SELECT id, aquarium_id, name, species, hunger, health, created_at FROM fish WHERE aquarium_id = ? ORDER BY id",
            (aquarium_id,),
        ).fetchall()
        return [
            Fish(
                id=row["id"],
                aquarium_id=row["aquarium_id"],
                name=row["name"],
                species=row["species"],
                hunger=row["hunger"],
                health=row["health"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def insert_fish(self, fish: Fish) -> Fish:
        cursor = self._connection.execute(
            "INSERT INTO fish (aquarium_id, name, species, hunger, health, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                fish.aquarium_id,
                fish.name,
                fish.species,
                fish.hunger,
                fish.health,
                fish.created_at.isoformat(),
            ),
        )
        self._connection.commit()
        return Fish(
            id=cursor.lastrowid,
            aquarium_id=fish.aquarium_id,
            name=fish.name,
            species=fish.species,
            hunger=fish.hunger,
            health=fish.health,
            created_at=fish.created_at,
        )

    def update_fish(self, fishes: Iterable[Fish]) -> None:
        self._connection.executemany(
            "UPDATE fish SET hunger = ?, health = ? WHERE id = ?",
            ((fish.hunger, fish.health, fish.id) for fish in fishes if fish.id is not None),
        )
        self._connection.commit()

    def delete_fish(self, fish_id: int) -> None:
        self._connection.execute("DELETE FROM fish WHERE id = ?", (fish_id,))
        self._connection.commit()

    def delete_aquarium(self, aquarium_id: int) -> None:
        self._connection.execute("DELETE FROM aquariums WHERE id = ?", (aquarium_id,))
        self._connection.commit()

    def tasks_for_aquarium(self, aquarium_id: int) -> list[Task]:
        rows = self._connection.execute(
            "SELECT id, aquarium_id, kind, interval_minutes, last_run_at FROM tasks WHERE aquarium_id = ? ORDER BY id",
            (aquarium_id,),
        ).fetchall()
        return [
            Task(
                id=row["id"],
                aquarium_id=row["aquarium_id"],
                kind=row["kind"],
                interval_minutes=row["interval_minutes"],
                last_run_at=datetime.fromisoformat(row["last_run_at"]),
            )
            for row in rows
        ]

    def upsert_task(self, task: Task) -> Task:
        if task.id is None:
            cursor = self._connection.execute(
                "INSERT INTO tasks (aquarium_id, kind, interval_minutes, last_run_at) VALUES (?, ?, ?, ?)",
                (
                    task.aquarium_id,
                    task.kind,
                    task.interval_minutes,
                    task.last_run_at.isoformat(),
                ),
            )
            self._connection.commit()
            return Task(
                id=cursor.lastrowid,
                aquarium_id=task.aquarium_id,
                kind=task.kind,
                interval_minutes=task.interval_minutes,
                last_run_at=task.last_run_at,
            )
        self._connection.execute(
            "UPDATE tasks SET interval_minutes = ?, last_run_at = ? WHERE id = ?",
            (task.interval_minutes, task.last_run_at.isoformat(), task.id),
        )
        self._connection.commit()
        return task

    def update_task_timestamp(self, task_id: int, timestamp: datetime) -> None:
        self._connection.execute(
            "UPDATE tasks SET last_run_at = ? WHERE id = ?",
            (timestamp.isoformat(), task_id),
        )
        self._connection.commit()

    def refresh_aquarium_environment(self, aquarium: Aquarium, temperature_delta: float, cleanliness_delta: float) -> Aquarium:
        current_temperature = aquarium.current_temperature + temperature_delta
        cleanliness = max(0.0, min(100.0, aquarium.cleanliness + cleanliness_delta))
        self._connection.execute(
            "UPDATE aquariums SET current_temperature = ?, cleanliness = ? WHERE id = ?",
            (current_temperature, cleanliness, aquarium.id),
        )
        self._connection.commit()
        return Aquarium(
            id=aquarium.id,
            name=aquarium.name,
            target_temperature=aquarium.target_temperature,
            current_temperature=current_temperature,
            cleanliness=cleanliness,
            last_cleaned_at=aquarium.last_cleaned_at,
        )

    def set_aquarium_cleaned(self, aquarium_id: int, timestamp: datetime) -> None:
        self._connection.execute(
            "UPDATE aquariums SET cleanliness = ?, last_cleaned_at = ? WHERE id = ?",
            (100.0, timestamp.isoformat(), aquarium_id),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def ensure_defaults(self) -> None:
        has_aquariums = self._connection.execute("SELECT 1 FROM aquariums LIMIT 1").fetchone()
        if has_aquariums:
            return
        now = datetime.now(timezone.utc)
        aquarium = self.upsert_aquarium(
            Aquarium(
                id=None,
                name="Aquário Principal",
                target_temperature=25.0,
                current_temperature=25.0,
                cleanliness=85.0,
                last_cleaned_at=now - timedelta(days=2),
            )
        )
        if aquarium.id is None:
            raise RuntimeError("Falha ao inicializar aquário padrão")
        species = [
            ("Coral Blue", "Peixe-palhaço"),
            ("Bolhas", "Tetra Neon"),
            ("Foguete", "Guppy"),
        ]
        for name, sp in species:
            self.insert_fish(
                Fish(
                    id=None,
                    aquarium_id=aquarium.id,
                    name=name,
                    species=sp,
                    hunger=45.0,
                    health=82.0,
                    created_at=now,
                )
            )
        reminders = [
            ("alimentacao", 240),
            ("limpeza", 1440),
            ("temperatura", 180),
        ]
        for kind, interval in reminders:
            self.upsert_task(
                Task(
                    id=None,
                    aquarium_id=aquarium.id,
                    kind=kind,
                    interval_minutes=interval,
                    last_run_at=now - timedelta(minutes=interval),
                )
            )


