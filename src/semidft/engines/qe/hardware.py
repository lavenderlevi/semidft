"""Hardware telemetry and execution planner for Ryzen 7 H 255 + Radeon 780M + 16GB RAM."""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from semidft.core.exceptions import QEConfigurationError


class HardwareResources(BaseModel):
    """Detected host CPU, memory, and iGPU capabilities."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cpu_model: str
    physical_cores: int
    logical_threads: int
    total_ram_gib: float
    available_ram_gib: float
    has_avx512: bool
    igpu_detected: bool
    igpu_model: str | None = None
    rocm_kfd_available: bool = False


class ExecutionPlan(BaseModel):
    """Resolved parallel execution parameters and environment variables for QE."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: Literal["cpu_hybrid", "rocm_igpu"]
    mpi_ranks: int
    npool: int
    omp_threads: int
    estimated_ram_gib: float
    env_vars: dict[str, str]
    rationale: str


def detect_hardware_resources() -> HardwareResources:
    """Inspect Linux /proc/cpuinfo, /proc/meminfo, and /dev/kfd for host hardware."""
    cpu_model = "Unknown CPU"
    has_avx512 = False
    logical_threads = os.cpu_count() or 4
    physical_cores = max(1, logical_threads // 2)

    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        text = cpuinfo.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("model name") and ":" in line:
                cpu_model = line.split(":", 1)[1].strip()
            elif line.startswith("cpu cores") and ":" in line:
                try:
                    physical_cores = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("flags") and "avx512f" in line:
                has_avx512 = True

    total_gib = 8.0
    avail_gib = 4.0
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                total_gib = round(kb / (1024.0 * 1024.0), 2)
            elif line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                avail_gib = round(kb / (1024.0 * 1024.0), 2)

    igpu_detected = "780M" in cpu_model or "Radeon" in cpu_model
    igpu_model = "AMD Radeon 780M (gfx1103)" if "780M" in cpu_model else None
    rocm_kfd = Path("/dev/kfd").exists()

    return HardwareResources(
        cpu_model=cpu_model,
        physical_cores=physical_cores,
        logical_threads=logical_threads,
        total_ram_gib=total_gib,
        available_ram_gib=avail_gib,
        has_avx512=has_avx512,
        igpu_detected=igpu_detected,
        igpu_model=igpu_model,
        rocm_kfd_available=rocm_kfd,
    )


def plan_execution_resources(
    hardware: HardwareResources,
    num_atoms: int,
    num_kpoints: int,
    backend: Literal["cpu_hybrid", "rocm_igpu"] = "cpu_hybrid",
    mpi_ranks_override: int | None = None,
    omp_threads_override: int | None = None,
    npool_override: int | None = None,
) -> ExecutionPlan:
    """Compute an execution plan protecting single-channel RAM bandwidth and capacity."""
    base_per_rank_gib = 0.35 + 0.025 * max(1, num_atoms)

    if backend == "rocm_igpu":
        required_uma_gib = max(2.0, base_per_rank_gib * 1.8)
        if hardware.available_ram_gib < required_uma_gib:
            raise QEConfigurationError(
                f"Insufficient UMA system RAM for rocm_igpu offload: "
                f"available={hardware.available_ram_gib:.2f} GiB, "
                f"required>={required_uma_gib:.2f} GiB."
            )
        omp = omp_threads_override or min(4, hardware.physical_cores)
        return ExecutionPlan(
            backend="rocm_igpu",
            mpi_ranks=1,
            npool=1,
            omp_threads=omp,
            estimated_ram_gib=round(required_uma_gib, 2),
            env_vars={
                "OMP_NUM_THREADS": str(omp),
                "OMP_PROC_BIND": "close",
                "OMP_PLACES": "cores",
                "HSA_OVERRIDE_GFX_VERSION": "11.0.0",
                "HSA_XNACK": "1",
            },
            rationale=("Single-rank ROCm/iGPU offload mode with UMA memory guard for Radeon 780M."),
        )

    if hardware.available_ram_gib < 1.0:
        raise QEConfigurationError(
            f"Insufficient available system RAM ({hardware.available_ram_gib:.2f} GiB < 1.0 GiB)."
        )

    if mpi_ranks_override is not None:
        ranks = mpi_ranks_override
        omp = omp_threads_override or 1
    elif hardware.available_ram_gib < 4.5 or num_atoms > 16:
        ranks = min(2, hardware.physical_cores)
        omp = omp_threads_override or 2
    else:
        ranks = min(4, hardware.physical_cores)
        omp = omp_threads_override or 1

    if npool_override is not None:
        npool = npool_override
    else:
        npool = ranks if num_kpoints >= ranks else 1

    est_ram = round(ranks * base_per_rank_gib, 2)
    return ExecutionPlan(
        backend="cpu_hybrid",
        mpi_ranks=ranks,
        npool=npool,
        omp_threads=omp,
        estimated_ram_gib=est_ram,
        env_vars={
            "OMP_NUM_THREADS": str(omp),
            "OMP_PROC_BIND": "close",
            "OMP_PLACES": "cores",
            "OPENBLAS_NUM_THREADS": str(omp),
        },
        rationale=(
            f"Zen 4 CPU hybrid profile ({ranks} MPI ranks x {omp} OMP threads, -nk {npool}) "
            "minimizing 3D FFT traffic across single-channel RAM."
        ),
    )
