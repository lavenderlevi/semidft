"""Calculation-type-specific convergence dispatcher [SPEC-01, SPEC-02]."""

from pydantic import BaseModel, ConfigDict, Field

from semidft.core.models import CalculationSpec, CalculationType, ValidationStatus
from semidft.engines.qe.convergence.cell import evaluate_cell_convergence
from semidft.engines.qe.convergence.electronic import evaluate_electronic_convergence
from semidft.engines.qe.convergence.ionic import evaluate_ionic_convergence
from semidft.engines.qe.output_parser import ParsedPWOutput


class ConvergenceSummary(BaseModel):
    """Detailed breakdown of electronic, ionic, and cell convergence checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    validation_status: ValidationStatus
    electronic_converged: bool
    ionic_converged: bool | None = None
    cell_converged: bool | None = None
    messages: list[str] = Field(default_factory=list)


def evaluate_calculation_convergence(
    spec: CalculationSpec,
    parsed: ParsedPWOutput | None,
) -> tuple[ValidationStatus, ConvergenceSummary]:
    """Dispatch convergence evaluation based on spec.calculation_type."""
    if parsed is None:
        summary = ConvergenceSummary(
            validation_status=ValidationStatus.PARSE_FAILED,
            electronic_converged=False,
            messages=["Output could not be parsed."],
        )
        return (ValidationStatus.PARSE_FAILED, summary)

    elec_ok, elec_msgs = evaluate_electronic_convergence(spec, parsed)
    all_msgs = list(elec_msgs)
    ionic_ok: bool | None = None
    cell_ok: bool | None = None

    if spec.calculation_type in (CalculationType.RELAX, CalculationType.VC_RELAX):
        ionic_ok, ionic_msgs = evaluate_ionic_convergence(spec, parsed)
        all_msgs.extend(ionic_msgs)

    if spec.calculation_type == CalculationType.VC_RELAX:
        cell_ok, cell_msgs = evaluate_cell_convergence(spec, parsed)
        all_msgs.extend(cell_msgs)

    overall_ok = elec_ok and (ionic_ok is not False) and (cell_ok is not False)
    status = ValidationStatus.CONVERGED if overall_ok else ValidationStatus.UNCONVERGED
    summary = ConvergenceSummary(
        validation_status=status,
        electronic_converged=elec_ok,
        ionic_converged=ionic_ok,
        cell_converged=cell_ok,
        messages=all_msgs,
    )
    return (status, summary)
