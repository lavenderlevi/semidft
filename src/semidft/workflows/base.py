"""Base workflow validation helpers enforcing SPEC-01 and SPEC-03."""

from pathlib import Path
from typing import Protocol

from semidft.core.exceptions import ConvergenceError
from semidft.core.models import CalculationSpec, RunManifest, StructureRecord


class PWRunnerCallable(Protocol):
    """Protocol for executing a single Quantum ESPRESSO pw.x calculation."""

    def __call__(
        self,
        run_dir: Path,
        structure: StructureRecord,
        spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
    ) -> RunManifest: ...


def default_pw_runner(
    run_dir: Path,
    structure: StructureRecord,
    spec: CalculationSpec,
    pseudo_sha256: dict[str, str],
) -> RunManifest:
    """Delegate execution to semidft.engines.qe.runner.execute_pw_calculation."""
    from semidft.engines.qe.runner import execute_pw_calculation

    return execute_pw_calculation(
        run_dir=run_dir,
        structure=structure,
        spec=spec,
        pseudo_sha256=pseudo_sha256,
    )


def require_converged_upstream(manifest: RunManifest, step_name: str) -> None:
    """Raise ConvergenceError if an upstream calculation is not COMPLETED and CONVERGED."""
    if not manifest.is_usable_for_downstream():
        raise ConvergenceError(
            f"Upstream step {step_name!r} ({manifest.calculation_id}) did not converge: "
            f"execution_status={manifest.execution_status.value}, "
            f"validation_status={manifest.validation_status.value}."
        )
