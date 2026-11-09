"""Ionic (`relax`) and variable-cell (`vc-relax`) optimization workflows [SPEC-02, SPEC-03]."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    CellType,
    RunManifest,
    StructureRecord,
)
from semidft.engines.qe.output_parser import parse_pw_output
from semidft.structures.validator import validate_structure
from semidft.workflows.base import (
    PWRunnerCallable,
    default_pw_runner,
    require_converged_upstream,
)


class RelaxationWorkflowResult(BaseModel):
    """Result of a structural relaxation (`relax` or `vc-relax`) workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: Path
    manifest: RunManifest
    initial_structure: StructureRecord
    relaxed_structure: StructureRecord


def extract_relaxed_structure(
    initial_structure: StructureRecord,
    pw_out_text: str,
) -> StructureRecord:
    """Extract the final relaxed crystal structure from pw.out and validate invariants."""
    parsed = parse_pw_output(pw_out_text)
    lattice = parsed.relaxed_lattice_angstrom or initial_structure.lattice_matrix_angstrom
    species = parsed.relaxed_species or initial_structure.species
    coords = parsed.relaxed_fractional_coords or initial_structure.fractional_coords

    relaxed = initial_structure.model_copy(
        update={
            "lattice_matrix_angstrom": lattice,
            "species": species,
            "fractional_coords": coords,
            "cell_type": CellType.RELAXED,
        }
    )
    return validate_structure(relaxed)


class RelaxationWorkflow:
    """Orchestrate `relax` or `vc-relax` optimization and verify convergence [SPEC-02, SPEC-03]."""

    def __init__(self, runner: PWRunnerCallable = default_pw_runner) -> None:
        self.runner = runner

    def run(
        self,
        run_dir: Path,
        structure: StructureRecord,
        spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
    ) -> RelaxationWorkflowResult:
        """Validate structure, run relaxation, check convergence, and return relaxed structure."""
        if spec.calculation_type not in (
            CalculationType.RELAX,
            CalculationType.VC_RELAX,
        ):
            raise ValueError(
                f"RelaxationWorkflow requires CalculationType.RELAX or VC_RELAX, "
                f"got {spec.calculation_type.value!r}."
            )

        validated_input = validate_structure(structure)
        manifest = self.runner(run_dir, validated_input, spec, pseudo_sha256)
        require_converged_upstream(manifest, spec.calculation_type.value)

        pw_out_path = run_dir / "output" / "pw.out"
        if pw_out_path.is_file():
            relaxed = extract_relaxed_structure(
                validated_input, pw_out_path.read_text(encoding="utf-8")
            )
        else:
            relaxed = validated_input.model_copy(update={"cell_type": CellType.RELAXED})

        return RelaxationWorkflowResult(
            run_dir=run_dir,
            manifest=manifest,
            initial_structure=validated_input,
            relaxed_structure=relaxed,
        )
