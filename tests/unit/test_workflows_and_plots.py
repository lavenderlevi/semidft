from pathlib import Path

import pytest

from semidft.analysis.density_of_states import DOSData
from semidft.analysis.visualization import plot_band_structure, plot_dos
from semidft.core.exceptions import ConvergenceError
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    CellType,
    ExecutionStatus,
    RunManifest,
    StructureRecord,
    ValidationStatus,
)
from semidft.structures.builder import build_reference_structure
from semidft.workflows.scf import resolve_scf_input_structure
from semidft.workflows.semiconductor import SemiconductorWorkflow


def test_scf_workflow_accepts_direct_validated_or_converged_relaxed_structure_spec_03() -> None:
    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    # Case 1: standalone SCF on validated structure without relaxation
    resolved_direct = resolve_scf_input_structure(si)
    assert resolved_direct.material_id == si.material_id

    # Case 2: SCF after unconverged vc-relax must raise ConvergenceError
    bad_relax = RunManifest(
        calculation_id="si-vcrelax-001",
        material_id="silicon-diamond",
        calculation_type=CalculationType.VC_RELAX,
        execution_status=ExecutionStatus.COMPLETED,
        validation_status=ValidationStatus.UNCONVERGED,
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
    with pytest.raises(ConvergenceError, match="did not converge"):
        resolve_scf_input_structure(si, relaxation_manifest=bad_relax, relaxed_structure=si)


def test_plot_band_structure_and_dos_create_pngs(tmp_path: Path) -> None:
    band_png = plot_band_structure(
        distances=[0.0, 0.5, 1.0],
        eigenvalues_ev=[[-2.0, 0.0, 1.1], [-1.5, -0.2, 0.6], [-1.0, -0.5, 1.5]],
        vbm_ev=0.0,
        labels=["GAMMA", None, "X"],
        output_path=tmp_path / "bands.png",
    )
    assert band_png.is_file()

    dos_png = plot_dos(
        DOSData(
            fermi_energy_ev=0.0,
            energies_ev=[-2.0, -1.0, 0.0, 1.0, 2.0],
            dos_states_per_ev=[1.2, 2.5, 0.0, 1.8, 3.1],
            integrated_dos_electrons=[1.0, 3.0, 4.0, 5.0, 8.0],
        ),
        output_path=tmp_path / "dos.png",
    )
    assert dos_png.is_file()


def test_semiconductor_workflow_stages_scf_and_cleans_wfc_spec_03(
    tmp_path: Path,
) -> None:
    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    base_spec = CalculationSpec(
        calculation_id="si-scf-001",
        material_id=si.material_id,
        calculation_type=CalculationType.SCF,
        pseudopotentials={"Si": "Si.UPF"},
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
    )

    def _fake_runner(
        run_dir: Path,
        structure: StructureRecord,
        spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
    ) -> RunManifest:
        if spec.calculation_type == CalculationType.SCF:
            save_dir = run_dir / "scratch" / f"{spec.calculation_id}.save"
            save_dir.mkdir(parents=True, exist_ok=True)
            (save_dir / "data-file-schema.xml").write_text("<xml/>", encoding="utf-8")
            (save_dir / "charge-density.dat").write_bytes(b"RHO")
            (run_dir / "scratch" / f"{spec.calculation_id}.wfc1").write_bytes(b"WFC")
        return RunManifest(
            calculation_id=spec.calculation_id,
            material_id=structure.material_id,
            calculation_type=spec.calculation_type,
            execution_status=ExecutionStatus.COMPLETED,
            validation_status=ValidationStatus.CONVERGED,
            exit_code=0,
            structure_hash="s" * 64,
            input_hash="i" * 64,
            qe_version="7.5",
            xc_functional="PBE",
            ecutwfc_ry=spec.ecutwfc_ry,
            ecutrho_ry=spec.ecutrho_ry,
            kpoints=spec.kpoints,
            pseudo_checksums=pseudo_sha256,
            total_energy_ev=-215.56,
        )

    wf = SemiconductorWorkflow(points_per_segment=10, runner=_fake_runner)
    res = wf.run(
        base_dir=tmp_path,
        initial_structure=si,
        scf_spec=base_spec,
        bands_spec=base_spec.model_copy(
            update={
                "calculation_id": "si-bands-001",
                "calculation_type": CalculationType.BANDS,
            }
        ),
        dos_spec=base_spec.model_copy(
            update={
                "calculation_id": "si-dos-001",
                "calculation_type": CalculationType.NSCF,
            }
        ),
        pseudo_sha256={"Si": "p" * 64},
    )
    assert res.scf.manifest.validation_status == ValidationStatus.CONVERGED
    assert (res.bands.staged_save_dir / "charge-density.dat").is_file()
    assert res.dos is not None
    assert (res.dos.staged_save_dir / "charge-density.dat").is_file()
    assert len(res.cleaned_wavefunction_files) == 1
