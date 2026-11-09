"""Serialization and loading of versioned RunManifest files."""

import json
from pathlib import Path

from semidft.core.models import RunManifest
from semidft.core.schemas import validate_schema_version


def save_manifest(run_dir: Path, manifest: RunManifest) -> Path:
    """Persist manifest.json atomically inside run_dir."""
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest_path


def load_manifest(run_dir: Path) -> RunManifest:
    """Load and schema-validate manifest.json from run_dir."""
    manifest_path = run_dir / "manifest.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_schema_version(raw)
    return RunManifest.model_validate(raw)
