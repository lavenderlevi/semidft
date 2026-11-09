from pathlib import Path

import pytest

from semidft.core.exceptions import StorageConflictError
from semidft.engines.qe.convergence.protocol import (
    ConvergenceProtocolConfig,
    SweepPointResult,
    select_converged_cutoff_pair,
    select_converged_kmesh,
)
from semidft.storage.artifacts import initialize_run_directory


def test_stage_a_cutoff_selection_lowest_cost_within_tolerances_spec_02() -> None:
    cfg = ConvergenceProtocolConfig(
        energy_per_atom_tolerance_ev=0.001,  # 1 meV/atom
        force_tolerance_ev_per_angstrom=0.005,
        stress_tolerance_gpa=0.05,
        band_gap_tolerance_ev=0.005,
    )
    # 2-atom Si primitive cell, USPP dual ratio 8:1
    sweep = [
        SweepPointResult(
            ecutwfc_ry=25.0,
            ecutrho_ry=200.0,
            kpoints=[8, 8, 8],
            total_energy_ev=-215.4000,
            max_force_ev_per_angstrom=0.001,
            stress_residual_gpa=0.08,
        ),
        SweepPointResult(
            ecutwfc_ry=30.0,
            ecutrho_ry=240.0,
            kpoints=[8, 8, 8],
            total_energy_ev=-215.4500,
            max_force_ev_per_angstrom=0.0005,
            stress_residual_gpa=0.02,
        ),
        SweepPointResult(
            ecutwfc_ry=35.0,
            ecutrho_ry=280.0,
            kpoints=[8, 8, 8],
            total_energy_ev=-215.4510,  # dE/atom = 0.0005 eV < 0.001 eV
            max_force_ev_per_angstrom=0.0004,
            stress_residual_gpa=0.015,
        ),
        SweepPointResult(
            ecutwfc_ry=40.0,
            ecutrho_ry=320.0,
            kpoints=[8, 8, 8],
            total_energy_ev=-215.4512,
            max_force_ev_per_angstrom=0.0004,
            stress_residual_gpa=0.014,
        ),
    ]
    selected = select_converged_cutoff_pair(sweep, num_atoms=2, config=cfg)
    assert selected.ecutwfc_ry == 30.0
    assert selected.ecutrho_ry == 240.0


def test_stage_b_kmesh_selection_checks_band_gap_shift_spec_02() -> None:
    cfg = ConvergenceProtocolConfig(
        energy_per_atom_tolerance_ev=0.001,
        band_gap_tolerance_ev=0.002,
    )
    sweep = [
        SweepPointResult(
            ecutwfc_ry=30.0,
            ecutrho_ry=240.0,
            kpoints=[6, 6, 6],
            total_energy_ev=-215.4500,
            band_gap_ev=0.610,
        ),
        SweepPointResult(
            ecutwfc_ry=30.0,
            ecutrho_ry=240.0,
            kpoints=[8, 8, 8],
            total_energy_ev=-215.4508,
            band_gap_ev=0.580,  # gap shift 0.030 eV > 0.002 eV
        ),
        SweepPointResult(
            ecutwfc_ry=30.0,
            ecutrho_ry=240.0,
            kpoints=[10, 10, 10],
            total_energy_ev=-215.4510,
            band_gap_ev=0.579,  # gap shift 0.001 eV <= 0.002 eV
        ),
    ]
    selected = select_converged_kmesh(sweep, num_atoms=2, config=cfg)
    assert selected.kpoints == [8, 8, 8]


def test_immutable_run_directory_prevents_overwrite(tmp_path: Path) -> None:
    run_dir = initialize_run_directory(tmp_path, "silicon-diamond", "si-scf-001")
    assert (run_dir / "input").is_dir()
    assert (run_dir / "output").is_dir()
    assert (run_dir / "scratch").is_dir()

    with pytest.raises(StorageConflictError, match="already exists"):
        initialize_run_directory(tmp_path, "silicon-diamond", "si-scf-001", overwrite=False)
