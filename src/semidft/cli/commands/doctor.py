"""Environment, QE executable, and hardware diagnostic command."""

import importlib.metadata
import json
import sys
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from semidft.core.exceptions import QEConfigurationError
from semidft.engines.qe.executable import discover_qe_executables
from semidft.engines.qe.hardware import (
    HardwareResources,
    detect_hardware_resources,
    plan_execution_resources,
)

console = Console()


def _build_benchmark_profiles(hw: HardwareResources) -> dict[str, Any]:
    """Compare candidate CPU MPI/OpenMP and ROCm iGPU execution profiles."""
    safe_hw = hw.model_copy(update={"available_ram_gib": max(hw.available_ram_gib, 8.0)})
    kpool_plan = plan_execution_resources(
        hardware=safe_hw,
        num_atoms=2,
        num_kpoints=29,
        backend="cpu_hybrid",
    )
    low_mem_hw = hw.model_copy(update={"available_ram_gib": 3.5})
    low_mem_plan = plan_execution_resources(
        hardware=low_mem_hw,
        num_atoms=16,
        num_kpoints=8,
        backend="cpu_hybrid",
    )
    try:
        igpu_plan = plan_execution_resources(
            hardware=safe_hw,
            num_atoms=2,
            num_kpoints=29,
            backend="rocm_igpu",
        )
        igpu_entry: dict[str, Any] = igpu_plan.model_dump()
    except QEConfigurationError as exc:
        igpu_entry = {"backend": "rocm_igpu", "error": str(exc)}

    return {
        "cpu_hybrid_kpool": kpool_plan.model_dump(),
        "cpu_hybrid_low_mem": low_mem_plan.model_dump(),
        "rocm_igpu": igpu_entry,
    }


def run_doctor(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON report to stdout."),
    benchmark: bool = typer.Option(
        False,
        "--benchmark",
        help="Compare candidate CPU MPI/OpenMP and ROCm iGPU execution profiles.",
    ),
) -> None:
    """Check Python libraries, QE executables, MPI runtime, and Ryzen/Radeon hardware."""
    packages = ["ase", "pymatgen", "spglib", "seekpath", "numpy", "scipy", "pydantic"]
    pkg_versions: dict[str, str | None] = {}
    for pkg in packages:
        try:
            pkg_versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pkg_versions[pkg] = None

    qe = discover_qe_executables()
    hw = detect_hardware_resources()
    recommended_plan = plan_execution_resources(
        hardware=hw, num_atoms=2, num_kpoints=29, backend="cpu_hybrid"
    )

    py_version = sys.version.split()[0]
    report: dict[str, Any] = {
        "python_ok": sys.version_info >= (3, 12),
        "python_version": py_version,
        "packages": pkg_versions,
        "qe_executables": qe.model_dump(),
        "hardware": hw.model_dump(),
        "recommended_default_plan": recommended_plan.model_dump(),
    }
    if benchmark:
        report["benchmark_profiles"] = _build_benchmark_profiles(hw)

    if json_output:
        typer.echo(json.dumps(report, indent=2))
        return

    table = Table(title="Semiconductor DFT Workflow — Environment & Hardware Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row("Python", "OK", py_version)
    for pkg, ver in pkg_versions.items():
        status = "OK" if ver else "MISSING"
        table.add_row(f"Package: {pkg}", status, ver or "Not installed")

    table.add_row(
        "QE pw.x",
        "OK" if qe.pw_path else "NOT FOUND",
        qe.pw_path or "Install quantum-espresso",
    )
    table.add_row(
        "QE bands.x",
        "OK" if qe.bands_path else "NOT FOUND",
        qe.bands_path or "Install quantum-espresso",
    )
    table.add_row(
        "QE dos.x",
        "OK" if qe.dos_path else "NOT FOUND",
        qe.dos_path or "Install quantum-espresso",
    )
    table.add_row(
        "MPI Launcher",
        "OK" if qe.mpirun_path else "NOT FOUND",
        qe.mpirun_path or "Install openmpi",
    )
    table.add_row(
        "CPU",
        "OK",
        f"{hw.cpu_model} ({hw.physical_cores}C/{hw.logical_threads}T)",
    )
    table.add_row(
        "System RAM",
        "OK",
        f"{hw.available_ram_gib:.2f} GiB free / {hw.total_ram_gib:.2f} GiB total",
    )
    table.add_row(
        "iGPU / ROCm",
        "OK" if hw.igpu_detected else "INFO",
        hw.igpu_model or "None",
    )
    table.add_row(
        "Recommended Plan",
        "OK",
        f"mpirun -np {recommended_plan.mpi_ranks} pw.x -nk {recommended_plan.npool} "
        f"(OMP={recommended_plan.omp_threads})",
    )
    if benchmark:
        profiles = report["benchmark_profiles"]
        for prof_name, prof_data in profiles.items():
            table.add_row(
                f"Benchmark: {prof_name}",
                "PROFILE",
                str(prof_data.get("rationale", prof_data.get("error", ""))),
            )
    console.print(table)
