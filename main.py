from __future__ import annotations

from pathlib import Path

from app.database import Database
from app.gui import run_app
from app.simulation import SimulationEngine


def main() -> None:
    base_path = Path(__file__).resolve().parent
    db_path = base_path / "aquarium.db"
    database = Database(db_path)
    database.ensure_defaults()
    simulation = SimulationEngine(database)
    try:
        run_app(simulation)
    finally:
        database.close()
        print("Gerenciador de aquario encerrado.")


if __name__ == "__main__":
    print("Iniciando gerenciador de aquario.")
    main()

