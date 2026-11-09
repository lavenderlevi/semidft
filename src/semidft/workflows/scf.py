"""SCF workflow supporting both relaxed structures and standalone validated structures [SPEC-03]."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from semidft.core.exceptions import ConvergenceError
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    RunManifest,
    StructureRecord,
)
from semidft.structures.validator import validate_structure
from semidft.workflows.base import (
    PWRunnerCallable,
    default_pw_runner,
    require_converged_upstream,
)


class SCFWorkflowResult(BaseModel):
    """Result of an electronic self-consistent field (`scf`) workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: Path
    manifest: RunManifest
    structure: StructureRecord


def resolve_scf_input_structure(
    initial_structure: StructureRecord,
    relaxation_manifest: RunManifest | None = None,
    relaxed_structure: StructureRecord | None = None,
) -> StructureRecord:
    """Resolve SCF input structure from a converged relaxation or validated input [SPEC-03]."""
    if relaxation_manifest is not None:
        require_converged_upstream(relaxation_manifest, "relaxation")
        if relaxed_structure is None:
            raise ConvergenceError(
                f"Relaxation {relaxation_manifest.calculation_id} converged, "
                "but relaxed_structure is missing."
            )
        return validate_structure(relaxed_structure)

    return validate_structure(initial_structure)


class SCFWorkflow:
    """Execute a self-consistent field (`scf`) ground-state calculation [SPEC-03]."""

    def __init__(self, runner: PWRunnerCallable = default_pw_runner) -> None:
        self.runner = runner

    def run(
        self,
        run_dir: Path,
        initial_structure: StructureRecord,
        spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
        relaxation_manifest: RunManifest | None = None,
        relaxed_structure: StructureRecord | None = None,
    ) -> SCFWorkflowResult:
        """Resolve input structure, run SCF, and enforce electronic convergence."""
        resolved_structure = resolve_scf_input_structure(
            initial_structure=initial_structure,
            relaxation_manifest=relaxation_manifest,
            relaxed_structure=relaxed_structure,
        )
        scf_spec = spec.model_copy(update={"calculation_type": CalculationType.SCF})
        manifest = self.runner(run_dir, resolved_structure, scf_spec, pseudo_sha256)
        require_converged_upstream(manifest, "scf")
        return SCFWorkflowResult(
            run_dir=run_dir,
            manifest=manifest,
            structure=resolved_structure,
        )
