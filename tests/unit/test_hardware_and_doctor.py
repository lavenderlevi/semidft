import pytest
from typer.testing import CliRunner

from semidft.cli.app import app
from semidft.core.exceptions import QEConfigurationError
from semidft.engines.qe.hardware import (
    HardwareResources,
    plan_execution_resources,
)


def _mock_ryzen_7_h255(mem_available_gib: float = 8.0) -> HardwareResources:
    return HardwareResources(
        cpu_model="AMD Ryzen 7 H 255 w/ Radeon 780M Graphics",
        physical_cores=8,
        logical_threads=16,
        total_ram_gib=14.0,
        available_ram_gib=mem_available_gib,
        has_avx512=True,
        igpu_detected=True,
        igpu_model="AMD Radeon 780M (gfx1103)",
        rocm_kfd_available=True,
    )


def test_cpu_hybrid_planner_uses_kpoint_pools_for_small_cell() -> None:
    hw = _mock_ryzen_7_h255(mem_available_gib=8.0)
    plan = plan_execution_resources(
        hardware=hw,
        num_atoms=2,
        num_kpoints=29,
        backend="cpu_hybrid",
    )
    assert plan.backend == "cpu_hybrid"
    assert plan.mpi_ranks == 4
    assert plan.npool == 4
    assert plan.omp_threads == 1
    assert plan.env_vars["OMP_NUM_THREADS"] == "1"
    assert plan.env_vars["OMP_PROC_BIND"] == "close"
    assert plan.env_vars["OMP_PLACES"] == "cores"


def test_cpu_hybrid_planner_reduces_ranks_on_low_memory_or_supercell() -> None:
    hw = _mock_ryzen_7_h255(mem_available_gib=3.2)
    plan = plan_execution_resources(
        hardware=hw,
        num_atoms=64,
        num_kpoints=4,
        backend="cpu_hybrid",
    )
    assert plan.mpi_ranks == 2
    assert plan.omp_threads == 2
    assert plan.npool in (1, 2)


def test_rocm_igpu_planner_enforces_single_rank_and_uma_guard() -> None:
    hw = _mock_ryzen_7_h255(mem_available_gib=6.0)
    plan = plan_execution_resources(
        hardware=hw,
        num_atoms=2,
        num_kpoints=16,
        backend="rocm_igpu",
    )
    assert plan.backend == "rocm_igpu"
    assert plan.mpi_ranks == 1
    assert plan.env_vars["HSA_OVERRIDE_GFX_VERSION"] == "11.0.0"
    assert plan.env_vars["HSA_XNACK"] == "1"

    hw_low = _mock_ryzen_7_h255(mem_available_gib=1.2)
    with pytest.raises(QEConfigurationError, match="Insufficient UMA system RAM"):
        plan_execution_resources(
            hardware=hw_low,
            num_atoms=16,
            num_kpoints=8,
            backend="rocm_igpu",
        )


def test_cli_doctor_runs_cleanly() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    assert '"python_ok": true' in result.stdout
