"""Lightweight SQLite provenance index over immutable calculation directories."""

import sqlite3
from pathlib import Path
from typing import Any

from semidft.core.models import RunManifest


class ProvenanceDatabase:
    """SQLite index tracking calculation manifests and input hashes."""

    def __init__(self, db_path: Path = Path("calculations/index.sqlite")) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calculations (
                    calculation_id TEXT PRIMARY KEY,
                    material_id TEXT NOT NULL,
                    calculation_type TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    exit_code INTEGER,
                    structure_hash TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    qe_version TEXT NOT NULL,
                    xc_functional TEXT NOT NULL,
                    total_energy_ev REAL,
                    run_dir TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_input_hash ON calculations(input_hash)")

    def upsert_manifest(self, manifest: RunManifest, run_dir: Path) -> None:
        """Insert or update a RunManifest summary row in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO calculations (
                    calculation_id, material_id, calculation_type,
                    execution_status, validation_status, exit_code,
                    structure_hash, input_hash, qe_version, xc_functional,
                    total_energy_ev, run_dir, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(calculation_id) DO UPDATE SET
                    execution_status = excluded.execution_status,
                    validation_status = excluded.validation_status,
                    exit_code = excluded.exit_code,
                    total_energy_ev = excluded.total_energy_ev,
                    run_dir = excluded.run_dir
                """,
                (
                    manifest.calculation_id,
                    manifest.material_id,
                    manifest.calculation_type.value,
                    manifest.execution_status.value,
                    manifest.validation_status.value,
                    manifest.exit_code,
                    manifest.structure_hash,
                    manifest.input_hash,
                    manifest.qe_version,
                    manifest.xc_functional,
                    manifest.total_energy_ev,
                    str(run_dir),
                    manifest.created_at_utc,
                ),
            )

    def get_manifest_record(self, calculation_id: str) -> dict[str, Any] | None:
        """Retrieve a single indexed calculation row by calculation_id."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM calculations WHERE calculation_id = ?",
                (calculation_id,),
            ).fetchone()
            return dict(row) if row else None

    def find_by_input_hash(self, input_hash: str) -> list[dict[str, Any]]:
        """Find all calculations matching a cryptographic input_hash."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM calculations WHERE input_hash = ? ORDER BY created_at_utc DESC",
                (input_hash,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_calculations(self) -> list[dict[str, Any]]:
        """Return all indexed calculations ordered by created_at_utc descending."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM calculations ORDER BY created_at_utc DESC"
            ).fetchall()
            return [dict(r) for r in rows]
