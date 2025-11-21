from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database import Database
from app.simulation import SimulationEngine


class SimulationEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test.db"
        self._database = Database(db_path)
        self._database.ensure_defaults()
        self._engine = SimulationEngine(self._database)

    def tearDown(self) -> None:
        self._database.close()
        self._temp_dir.cleanup()

    def test_feed_fish_reduces_hunger(self) -> None:
        aquarium = self._engine.aquariums()[0]
        self.assertIsNotNone(aquarium.id)
        fishes = self._engine.fish_for(aquarium.id)
        start = fishes[0].hunger
        self._engine.feed_fish(aquarium.id)
        self._engine.reload()
        fishes_after = self._engine.fish_for(aquarium.id)
        self.assertLess(fishes_after[0].hunger, start)

    def test_due_tasks_detects_overdue(self) -> None:
        aquarium = self._engine.aquariums()[0]
        self.assertIsNotNone(aquarium.id)
        task = self._engine.tasks_for(aquarium.id)[0]
        overdue = datetime.now(timezone.utc) - timedelta(minutes=task.interval_minutes + 5)
        if task.id is not None:
            self._database.update_task_timestamp(task.id, overdue)
        self._engine.reload()
        due = self._engine.due_tasks()
        self.assertTrue(any(entry[0].id == task.id for entry in due))

    def test_tick_decreases_cleanliness(self) -> None:
        aquarium = self._engine.aquariums()[0]
        baseline = aquarium.cleanliness
        self._engine._last_tick = datetime.now(timezone.utc) - timedelta(minutes=90)
        self._engine.tick()
        updated = self._engine.aquariums()[0]
        self.assertLess(updated.cleanliness, baseline)

    def test_delete_aquarium_removes_records(self) -> None:
        created = self._engine.create_aquarium("Sala Verde", 24.0)
        self.assertIsNotNone(created.id)
        identifiers = {aquarium.id for aquarium in self._engine.aquariums()}
        self.assertIn(created.id, identifiers)
        if created.id is not None:
            self._engine.delete_aquarium(created.id)
        identifiers_after = {aquarium.id for aquarium in self._engine.aquariums()}
        self.assertNotIn(created.id, identifiers_after)


if __name__ == "__main__":
    unittest.main()

