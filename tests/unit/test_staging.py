from pathlib import Path

import pytest

from semidft.core.exceptions import ConvergenceError
from semidft.core.models import (
    CalculationType,
    ExecutionStatus,
    RunManifest,
    ValidationStatus,
)
from semidft.storage.staging import (
    cleanup_temporary_wavefunctions,
    stage_scf_reference_data,
)


def _make_manifest(
    calc_id: str,
    exec_status: ExecutionStatus,
    val_status: ValidationStatus,
) -> RunManifest:
    return RunManifest(
        calculation_id=calc_id,
        material_id="silicon-diamond",
        calculation_type=CalculationType.SCF,
        execution_status=exec_status,
        validation_status=val_status,
        exit_code=0,
        structure_hash="s" * 64,
        input_hash="i" * 64,
        qe_version="7.5",
        xc_functional="PBE",
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        pseudo_checksums={"Si": "p" * 64},
    )


def test_stage_scf_reference_copies_charge_density_and_skips_wfc_spec_03(
    tmp_path: Path,
) -> None:
    scf_dir = tmp_path / "scf-001"
    save_dir = scf_dir / "scratch" / "scf-001.save"
    save_dir.mkdir(parents=True)
    (save_dir / "data-file-schema.xml").write_text("<qes:espresso/>", encoding="utf-8")
    (save_dir / "charge-density.dat").write_bytes(b"RHO_DATA")
    (save_dir / "wfc1.dat").write_bytes(b"HEAVY_WFC")

    bands_dir = tmp_path / "bands-001"
    (bands_dir / "scratch").mkdir(parents=True)

    scf_manifest = _make_manifest("scf-001", ExecutionStatus.COMPLETED, ValidationStatus.CONVERGED)
    staged_save = stage_scf_reference_data(
        scf_run_dir=scf_dir,
        scf_manifest=scf_manifest,
        target_run_dir=bands_dir,
        target_prefix="bands-001",
    )

    assert (staged_save / "data-file-schema.xml").is_file()
    assert (staged_save / "charge-density.dat").is_file()
    assert not (staged_save / "wfc1.dat").exists()


def test_stage_scf_rejects_unconverged_scf_spec_01_03(tmp_path: Path) -> None:
    scf_dir = tmp_path / "scf-bad"
    bands_dir = tmp_path / "bands-001"
    unconverged = _make_manifest("scf-bad", ExecutionStatus.COMPLETED, ValidationStatus.UNCONVERGED)

    with pytest.raises(ConvergenceError, match="not usable for downstream"):
        stage_scf_reference_data(scf_dir, unconverged, bands_dir, "bands-001")


def test_cleanup_temporary_wavefunctions_preserves_charge_density_spec_03(
    tmp_path: Path,
) -> None:
    scf_dir = tmp_path / "scf-001"
    scratch = scf_dir / "scratch"
    save_dir = scratch / "scf-001.save"
    save_dir.mkdir(parents=True)
    (save_dir / "charge-density.dat").write_bytes(b"RHO")
    (save_dir / "data-file-schema.xml").write_text("<xml/>", encoding="utf-8")
    wfc_file = scratch / "scf-001.wfc1"
    wfc_file.write_bytes(b"WFC")

    bands_manifest = _make_manifest(
        "bands-001", ExecutionStatus.COMPLETED, ValidationStatus.CONVERGED
    )
    dos_manifest = _make_manifest("dos-001", ExecutionStatus.COMPLETED, ValidationStatus.CONVERGED)

    removed = cleanup_temporary_wavefunctions(scf_dir, [bands_manifest, dos_manifest])
    assert wfc_file in removed
    assert not wfc_file.exists()
    assert (save_dir / "charge-density.dat").is_file()
    assert (save_dir / "data-file-schema.xml").is_file()
