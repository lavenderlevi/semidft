"""Immutable calculation directory initialization and checksum verification."""

from pathlib import Path

from semidft.core.exceptions import StorageConflictError
from semidft.core.hashing import compute_file_sha256


def initialize_run_directory(
    base_dir: Path,
    material_id: str,
    calculation_id: str,
    overwrite: bool = False,
) -> Path:
    """Create calculations/<material_id>/runs/<calculation_id>/{input,output,scratch}."""
    run_dir = base_dir / material_id / "runs" / calculation_id
    if run_dir.exists() and not overwrite:
        raise StorageConflictError(
            f"Calculation directory {run_dir} already exists. "
            "Use a new calculation_id or pass overwrite=True explicitly."
        )
    for sub in ("input", "output", "scratch"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    return run_dir


def write_checksums_file(run_dir: Path) -> Path:
    """Compute SHA-256 checksums for all input/ and output/ files in run_dir."""
    lines: list[str] = []
    for folder in ("input", "output"):
        target_dir = run_dir / folder
        if target_dir.is_dir():
            for file_path in sorted(target_dir.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(run_dir).as_posix()
                    lines.append(f"{compute_file_sha256(file_path)}  {rel}")
    checksum_path = run_dir / "checksums.sha256"
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path
