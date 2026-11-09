"""Variable-cell convergence validator separating press_conv_thr and stress tolerance [SPEC-02]."""

from semidft.core.models import CalculationSpec
from semidft.engines.qe.output_parser import ParsedPWOutput


def evaluate_cell_convergence(
    spec: CalculationSpec,
    parsed: ParsedPWOutput,
) -> tuple[bool, list[str]]:
    """Verify hydrostatic pressure (press_conv_thr) and optional stress component tolerance."""
    messages: list[str] = []
    if parsed.pressure_gpa is None:
        return (False, ["Cell pressure/stress output is missing for vc-relax."])

    if abs(parsed.pressure_gpa) > spec.pressure_tolerance_gpa:
        return (
            False,
            [
                f"Residual hydrostatic pressure (|{parsed.pressure_gpa:.4f}| GPa) "
                f"exceeds pressure_tolerance_gpa ({spec.pressure_tolerance_gpa:.4f} GPa)."
            ],
        )

    if (
        spec.stress_tolerance_gpa is not None
        and parsed.max_stress_component_gpa is not None
        and parsed.max_stress_component_gpa > spec.stress_tolerance_gpa
    ):
        return (
            False,
            [
                f"Maximum stress tensor component ({parsed.max_stress_component_gpa:.4f} GPa) "
                f"exceeds post-processing stress_tolerance_gpa "
                f"({spec.stress_tolerance_gpa:.4f} GPa)."
            ],
        )

    messages.append(f"Variable-cell relaxation converged (P={parsed.pressure_gpa:.4f} GPa).")
    return (True, messages)
