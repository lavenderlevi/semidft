"""Two-stage plane-wave cutoff and k-point convergence protocol [SPEC-02]."""

from pydantic import BaseModel, ConfigDict, Field

from semidft.core.exceptions import ConvergenceError
from semidft.core.schemas import CURRENT_SCHEMA_VERSION


class ConvergenceProtocolConfig(BaseModel):
    """Configurable tolerances for Stage A (cutoff) and Stage B (k-point) sweeps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    energy_per_atom_tolerance_ev: float = 0.001
    force_tolerance_ev_per_angstrom: float = 0.005
    stress_tolerance_gpa: float = 0.05
    band_gap_tolerance_ev: float = 0.002
    stress_metric_name: str = "pressure_residual_gpa"


class SweepPointResult(BaseModel):
    """Numerical result of a single convergence sweep point on fixed geometry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ecutwfc_ry: float
    ecutrho_ry: float
    kpoints: list[int]
    total_energy_ev: float
    max_force_ev_per_angstrom: float = 0.0
    stress_residual_gpa: float = 0.0
    band_gap_ev: float | None = None
    converged_scf: bool = True


class TwoStageConvergenceResult(BaseModel):
    """Complete record of Stage A and Stage B sweeps and selected parameters [SPEC-02]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = CURRENT_SCHEMA_VERSION
    selected_parameters: dict[str, float | list[int]]
    criteria: dict[str, bool]
    selection_basis: str = "lowest_cost_configuration_within_tolerances"
    stage_a_cutoff_sweep: list[SweepPointResult] = Field(default_factory=list)
    stage_b_kpoint_sweep: list[SweepPointResult] = Field(default_factory=list)


def select_converged_cutoff_pair(
    points: list[SweepPointResult],
    num_atoms: int,
    config: ConvergenceProtocolConfig,
) -> SweepPointResult:
    """Select the lowest-cost (ecutwfc_ry, ecutrho_ry) pair satisfying Stage A tolerances."""
    if len(points) < 2:
        raise ConvergenceError("Stage A cutoff convergence requires at least 2 sweep points.")

    ordered = sorted(points, key=lambda p: p.ecutwfc_ry)
    for idx in range(len(ordered) - 1):
        curr = ordered[idx]
        nxt = ordered[idx + 1]
        if not curr.converged_scf or not nxt.converged_scf:
            continue
        de_atom = abs(nxt.total_energy_ev - curr.total_energy_ev) / max(1, num_atoms)
        force_ok = curr.max_force_ev_per_angstrom <= config.force_tolerance_ev_per_angstrom
        stress_ok = abs(curr.stress_residual_gpa) <= config.stress_tolerance_gpa
        if de_atom <= config.energy_per_atom_tolerance_ev and force_ok and stress_ok:
            return curr

    raise ConvergenceError(
        "Stage A cutoff sweep did not reach energy/force/stress tolerances within tested range."
    )


def select_converged_kmesh(
    points: list[SweepPointResult],
    num_atoms: int,
    config: ConvergenceProtocolConfig,
) -> SweepPointResult:
    """Select the lowest-cost k-point mesh satisfying Stage B energy and band-gap tolerances."""
    if len(points) < 2:
        raise ConvergenceError("Stage B k-point convergence requires at least 2 sweep points.")

    ordered = sorted(points, key=lambda p: p.kpoints[0] * p.kpoints[1] * p.kpoints[2])
    for idx in range(len(ordered) - 1):
        curr = ordered[idx]
        nxt = ordered[idx + 1]
        if not curr.converged_scf or not nxt.converged_scf:
            continue
        de_atom = abs(nxt.total_energy_ev - curr.total_energy_ev) / max(1, num_atoms)
        gap_ok = True
        if curr.band_gap_ev is not None and nxt.band_gap_ev is not None:
            gap_ok = abs(nxt.band_gap_ev - curr.band_gap_ev) <= config.band_gap_tolerance_ev
        if de_atom <= config.energy_per_atom_tolerance_ev and gap_ok:
            return curr

    raise ConvergenceError(
        "Stage B k-point sweep did not reach energy and band-gap tolerances within tested range."
    )
