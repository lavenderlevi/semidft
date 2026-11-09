"""Electronic convergence validators for scf, nscf, and bands calculations [SPEC-02]."""

from semidft.core.models import CalculationSpec, CalculationType
from semidft.engines.qe.output_parser import ParsedPWOutput


def evaluate_electronic_convergence(
    spec: CalculationSpec,
    parsed: ParsedPWOutput,
) -> tuple[bool, list[str]]:
    """Evaluate electronic convergence according to calculation_type."""
    messages: list[str] = []
    if not parsed.job_done:
        return (False, ["QE output is missing 'JOB DONE.' marker."])

    if spec.calculation_type in (CalculationType.NSCF, CalculationType.BANDS):
        if parsed.scf_not_converged_flag:
            return (
                False,
                [f"{spec.calculation_type.value} reported an electronic solver failure."],
            )
        if parsed.num_kpoints_computed <= 0 and not parsed.eigenvalues_ev:
            return (
                False,
                [f"{spec.calculation_type.value} output contains no k-point eigenvalues."],
            )
        messages.append(
            f"{spec.calculation_type.value} non-self-consistent eigenvalue evaluation completed."
        )
        return (True, messages)

    # Self-consistent types: scf, relax, vc-relax
    if not parsed.scf_converged_flag or parsed.scf_not_converged_flag:
        return (False, ["Electronic SCF loop did not achieve self-consistency."])
    if parsed.total_energy_ev is None:
        return (False, ["Total energy is missing from SCF output."])
    if (
        parsed.estimated_scf_accuracy_ry is not None
        and parsed.estimated_scf_accuracy_ry > spec.conv_thr_ry * 10.0
    ):
        return (
            False,
            [
                f"Estimated SCF accuracy ({parsed.estimated_scf_accuracy_ry:.2e} Ry) "
                f"exceeds threshold ({spec.conv_thr_ry:.2e} Ry)."
            ],
        )

    messages.append("Electronic SCF self-consistency verified.")
    return (True, messages)
