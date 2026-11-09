"""Tier 3 resource-controlled QE SCF integration test."""

from pathlib import Path

import pytest

from semidft.core.models import CalculationSpec, CalculationType, CellType, ValidationStatus
from semidft.engines.qe.executable import discover_qe_executables
from semidft.engines.qe.runner import execute_pw_calculation
from semidft.structures.builder import build_reference_structure


@pytest.mark.integration
def test_qe_silicon_scf_integration(tmp_path: Path) -> None:
    qe = discover_qe_executables()
    upf_path = Path("data/pseudopotentials/sssp-pbe-v2/Si.UPF")
    if not qe.pw_path or not upf_path.is_file():
        pytest.skip("Requires local pw.x executable and SSSP Si.UPF")

    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    spec = CalculationSpec(
        calculation_id="si-int-scf-001",
        material_id=si.material_id,
        calculation_type=CalculationType.SCF,
        pseudopotentials={"Si": "Si.UPF"},
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[4, 4, 4],
        mpi_ranks=2,
        npool=2,
        omp_threads=1,
    )
    run_dir = tmp_path / "si-int-scf-001"
    for sub in ("input", "output", "scratch"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    manifest = execute_pw_calculation(
        run_dir=run_dir,
        structure=si,
        spec=spec,
        pseudo_sha256={"Si": "integration_test"},
        pw_executable=qe.pw_path,
        mpirun_executable=qe.mpirun_path,
        timeout_seconds=180.0,
    )
    assert manifest.validation_status == ValidationStatus.CONVERGED
