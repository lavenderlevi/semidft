"""Tier 3 resource-controlled QE Density of States (DOS) integration test."""

from pathlib import Path

import pytest

from semidft.core.models import CalculationSpec, CalculationType, CellType, ValidationStatus
from semidft.engines.qe.executable import discover_qe_executables
from semidft.structures.builder import build_reference_structure
from semidft.workflows.dos import DOSWorkflow
from semidft.workflows.scf import SCFWorkflow


@pytest.mark.integration
def test_qe_silicon_dos_integration(tmp_path: Path) -> None:
    qe = discover_qe_executables()
    upf_path = Path("data/pseudopotentials/sssp-pbe-v2/Si.UPF")
    if not qe.pw_path or not qe.dos_path or not upf_path.is_file():
        pytest.skip("Requires local pw.x, dos.x, and SSSP Si.UPF")

    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    scf_spec = CalculationSpec(
        calculation_id="si-int-scf",
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
    dos_spec = CalculationSpec(
        calculation_id="si-int-dos",
        material_id=si.material_id,
        calculation_type=CalculationType.NSCF,
        pseudopotentials={"Si": "Si.UPF"},
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        occupations="tetrahedra",
        mpi_ranks=2,
        npool=2,
        omp_threads=1,
    )
    scf_dir = tmp_path / "scf"
    dos_dir = tmp_path / "dos"
    scf_res = SCFWorkflow().run(scf_dir, si, scf_spec, {"Si": "integration_test"})
    dos_res = DOSWorkflow().run(
        scf_run_dir=scf_dir,
        scf_manifest=scf_res.manifest,
        dos_run_dir=dos_dir,
        structure=si,
        spec=dos_spec,
        pseudo_sha256={"Si": "integration_test"},
    )
    assert dos_res.manifest.validation_status == ValidationStatus.CONVERGED
