"""Subprocess runner for Quantum ESPRESSO separating ExecutionStatus and ValidationStatus."""

import os
import subprocess
import time
from pathlib import Path

from semidft.core.hashing import compute_input_hash, compute_structure_hash
from semidft.core.models import (
    CalculationSpec,
    ExecutionStatus,
    RunManifest,
    StructureRecord,
    ValidationStatus,
)
from semidft.engines.qe.convergence.validation import evaluate_calculation_convergence
from semidft.engines.qe.executable import discover_qe_executables
from semidft.engines.qe.hardware import (
    detect_hardware_resources,
    plan_execution_resources,
)
from semidft.engines.qe.input_generator import generate_pw_input
from semidft.engines.qe.output_parser import parse_pw_output
from semidft.storage.artifacts import write_checksums_file
from semidft.storage.manifest import save_manifest
from semidft.structures.cif_io import write_cif


def build_qe_command(
    executable: str,
    input_file: Path,
    mpi_launcher: str | None,
    mpi_ranks: int,
    npool: int,
) -> list[str]:
    """Construct argument list for subprocess.run(..., shell=False)."""
    cmd: list[str] = []
    if mpi_launcher and mpi_ranks > 1:
        cmd.extend([mpi_launcher, "-np", str(mpi_ranks)])
    cmd.append(executable)
    if npool > 1 and executable.endswith("pw.x"):
        cmd.extend(["-nk", str(npool)])
    cmd.extend(["-in", str(input_file)])
    return cmd


def _resolve_pseudo_dir(run_dir: Path, pseudo_dir: Path) -> Path:
    """Resolve pseudopotential directory for a QE calculation."""
    if (run_dir / pseudo_dir).is_dir():
        return (run_dir / pseudo_dir).resolve()
    if pseudo_dir != Path("./pseudo") and pseudo_dir.is_dir():
        return pseudo_dir.resolve()
    default_sssp = Path("data/pseudopotentials/sssp-pbe-v2")
    if default_sssp.is_dir():
        return default_sssp.resolve()
    return (run_dir / pseudo_dir).resolve()


def execute_pw_calculation(
    run_dir: Path,
    structure: StructureRecord,
    spec: CalculationSpec,
    pseudo_sha256: dict[str, str],
    pw_executable: str = "pw.x",
    mpirun_executable: str | None = "mpirun",
    qe_version: str = "7.5",
    timeout_seconds: float = 1800.0,
    pseudo_dir: Path = Path("./pseudo"),
    kpath_crystal_b: list[tuple[float, float, float, int]] | None = None,
) -> RunManifest:
    """Prepare inputs, execute pw.x, parse output, and record orthogonal statuses [SPEC-01]."""
    if pw_executable == "pw.x" or mpirun_executable == "mpirun":
        discovered = discover_qe_executables()
        if pw_executable == "pw.x" and discovered.pw_path:
            pw_executable = discovered.pw_path
        if mpirun_executable == "mpirun" and discovered.mpirun_path:
            mpirun_executable = discovered.mpirun_path

    hw = detect_hardware_resources()
    num_k = (
        len(kpath_crystal_b)
        if kpath_crystal_b is not None
        else spec.kpoints[0] * spec.kpoints[1] * spec.kpoints[2]
    )
    plan = plan_execution_resources(
        hardware=hw,
        num_atoms=len(structure.species),
        num_kpoints=num_k,
        backend=spec.execution_backend,
        mpi_ranks_override=spec.mpi_ranks,
        omp_threads_override=spec.omp_threads,
        npool_override=spec.npool,
    )

    input_dir = run_dir / "input"
    output_dir = run_dir / "output"
    scratch_dir = run_dir / "scratch"
    analysis_dir = run_dir / "analysis"
    for d in (input_dir, output_dir, scratch_dir, analysis_dir):
        d.mkdir(parents=True, exist_ok=True)

    pw_in_path = input_dir / "pw.in"
    pw_out_path = output_dir / "pw.out"
    resolved_pseudo_dir = _resolve_pseudo_dir(run_dir, pseudo_dir)

    write_cif(structure, input_dir / "input_structure.cif")
    pw_in_text = generate_pw_input(
        structure=structure,
        spec=spec,
        pseudo_dir=resolved_pseudo_dir,
        outdir=scratch_dir.resolve(),
        prefix=spec.calculation_id,
        kpath_crystal_b=kpath_crystal_b,
    )
    pw_in_path.write_text(pw_in_text, encoding="utf-8")

    manifest = RunManifest(
        calculation_id=spec.calculation_id,
        material_id=spec.material_id,
        calculation_type=spec.calculation_type,
        execution_status=ExecutionStatus.PREPARED,
        validation_status=ValidationStatus.NOT_EVALUATED,
        structure_hash=compute_structure_hash(structure),
        input_hash=compute_input_hash(structure, spec, pseudo_sha256, qe_version=qe_version),
        qe_version=qe_version,
        xc_functional=spec.xc_functional,
        ecutwfc_ry=spec.ecutwfc_ry,
        ecutrho_ry=spec.ecutrho_ry,
        kpoints=spec.kpoints,
        pseudo_checksums=pseudo_sha256,
    )
    save_manifest(run_dir, manifest)

    cmd = build_qe_command(
        executable=pw_executable,
        input_file=pw_in_path.resolve(),
        mpi_launcher=mpirun_executable,
        mpi_ranks=plan.mpi_ranks,
        npool=plan.npool,
    )
    env = {**os.environ, **plan.env_vars}

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=run_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        wall_s = round(time.monotonic() - t0, 3)
        pw_out_path.write_text(proc.stdout, encoding="utf-8")
        if proc.stderr:
            (output_dir / "pw.err").write_text(proc.stderr, encoding="utf-8")

        exec_status = ExecutionStatus.COMPLETED if proc.returncode == 0 else ExecutionStatus.FAILED
        parsed = parse_pw_output(proc.stdout) if proc.stdout.strip() else None
        val_status, conv_summary = evaluate_calculation_convergence(spec, parsed)

        final_manifest = manifest.model_copy(
            update={
                "execution_status": exec_status,
                "validation_status": val_status,
                "exit_code": proc.returncode,
                "validation_messages": conv_summary.messages,
                "total_energy_ev": parsed.total_energy_ev if parsed else None,
                "fermi_energy_ev": parsed.fermi_energy_ev if parsed else None,
                "max_force_ev_per_angstrom": parsed.max_force_ev_per_angstrom if parsed else None,
                "pressure_gpa": parsed.pressure_gpa if parsed else None,
                "wall_time_seconds": wall_s,
            }
        )
    except subprocess.TimeoutExpired:
        wall_s = round(time.monotonic() - t0, 3)
        final_manifest = manifest.model_copy(
            update={
                "execution_status": ExecutionStatus.INTERRUPTED,
                "validation_status": ValidationStatus.NOT_EVALUATED,
                "validation_messages": [f"Timed out after {timeout_seconds}s."],
                "wall_time_seconds": wall_s,
            }
        )

    save_manifest(run_dir, final_manifest)
    write_checksums_file(run_dir)
    return final_manifest
