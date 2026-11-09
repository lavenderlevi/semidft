"""Ionic relaxation convergence validator checking etot_conv_thr and forc_conv_thr [SPEC-02]."""

from semidft.core.models import CalculationSpec
from semidft.engines.qe.output_parser import ParsedPWOutput


def evaluate_ionic_convergence(
    spec: CalculationSpec,
    parsed: ParsedPWOutput,
) -> tuple[bool, list[str]]:
    """Verify BFGS completion, energy_tolerance_ev (etot_conv_thr), and force tolerance."""
    messages: list[str] = []
    if not parsed.bfgs_converged_flag:
        return (False, ["BFGS ionic relaxation did not reach convergence marker."])

    if (
        parsed.final_energy_change_ev is not None
        and parsed.final_energy_change_ev > spec.energy_tolerance_ev
    ):
        return (
            False,
            [
                f"Final ionic energy change ({parsed.final_energy_change_ev:.6f} eV) "
                f"exceeds energy_tolerance_ev ({spec.energy_tolerance_ev:.6f} eV)."
            ],
        )

    if parsed.max_force_ev_per_angstrom is None:
        return (False, ["Atomic forces missing from relaxation output."])
    if parsed.max_force_ev_per_angstrom > spec.force_tolerance_ev_per_angstrom:
        return (
            False,
            [
                f"Maximum atomic force ({parsed.max_force_ev_per_angstrom:.5f} eV/Å) "
                f"exceeds force_tolerance_ev_per_angstrom "
                f"({spec.force_tolerance_ev_per_angstrom:.5f} eV/Å)."
            ],
        )

    messages.append(
        f"Ionic relaxation converged (max_force={parsed.max_force_ev_per_angstrom:.5f} eV/Å)."
    )
    return (True, messages)
