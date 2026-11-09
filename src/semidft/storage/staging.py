"""Isolated SCF artifact staging and dependency-aware wavefunction cleanup [SPEC-03]."""

import shutil
from pathlib import Path

from semidft.core.exceptions import ConvergenceError
from semidft.core.models import RunManifest

REQUIRED_SCF_SAVE_PATTERNS: tuple[str, ...] = (
    "data-file-schema.xml",
    "charge-density.dat",
    "charge-density.hdf5",
    "paw.txt",
    "*.UPF",
    "*.upf",
)


def stage_scf_reference_data(
    scf_run_dir: Path,
    scf_manifest: RunManifest,
    target_run_dir: Path,
    target_prefix: str,
) -> Path:
    """Copy required SCF charge-density and XML schema into an isolated staging directory."""
    if not scf_manifest.is_usable_for_downstream():
        raise ConvergenceError(
            f"Upstream SCF run {scf_manifest.calculation_id!r} is not usable for downstream "
            f"(execution={scf_manifest.execution_status.value}, "
            f"validation={scf_manifest.validation_status.value})."
        )

    source_save = scf_run_dir / "scratch" / f"{scf_manifest.calculation_id}.save"
    if not source_save.is_dir():
        raise ConvergenceError(f"Upstream SCF save directory not found: {source_save}")

    target_save = target_run_dir / "scratch" / f"{target_prefix}.save"
    target_save.mkdir(parents=True, exist_ok=True)

    copied_any = False
    for pattern in REQUIRED_SCF_SAVE_PATTERNS:
        for src_file in source_save.glob(pattern):
            if src_file.is_file():
                shutil.copy2(src_file, target_save / src_file.name)
                copied_any = True

    if not copied_any:
        raise ConvergenceError(f"No charge-density or XML schema files found in {source_save}")

    return target_save


def cleanup_temporary_wavefunctions(
    run_dir: Path,
    dependent_manifests: list[RunManifest],
) -> list[Path]:
    """Remove temporary .wfc* and .mix* files after all downstream dependents have converged."""
    for dep in dependent_manifests:
        if not dep.is_usable_for_downstream():
            raise ConvergenceError(
                f"Cannot clean temporary wavefunctions in {run_dir}: "
                f"dependent calculation {dep.calculation_id!r} is not CONVERGED."
            )

    scratch = run_dir / "scratch"
    if not scratch.is_dir():
        return []

    removed: list[Path] = []
    for pattern in ("*.wfc*", "*.mix*", "*/wfc*.dat", "*/wfc*.hdf5"):
        for candidate in sorted(scratch.glob(pattern)):
            if candidate.is_file():
                candidate.unlink()
                removed.append(candidate)

    return removed
