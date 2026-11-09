"""End-to-end semiconductor workflow orchestrating relax -> scf -> (bands, dos) [SPEC-03]."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from semidft.analysis.gap_classifier import ExperimentalGapReference
from semidft.core.models import CalculationSpec, StructureRecord
from semidft.storage.staging import cleanup_temporary_wavefunctions
from semidft.workflows.bands import BandsWorkflow, BandsWorkflowResult
from semidft.workflows.base import PWRunnerCallable, default_pw_runner
from semidft.workflows.dos import DOSWorkflow, DOSWorkflowResult
from semidft.workflows.relaxation import RelaxationWorkflow, RelaxationWorkflowResult
from semidft.workflows.scf import SCFWorkflow, SCFWorkflowResult


class SemiconductorWorkflowResult(BaseModel):
    """Aggregated results of a multi-step semiconductor characterization pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relaxation: RelaxationWorkflowResult | None = None
    scf: SCFWorkflowResult
    bands: BandsWorkflowResult
    dos: DOSWorkflowResult | None = None
    cleaned_wavefunction_files: list[Path]


class SemiconductorWorkflow:
    """Orchestrate optional relaxation, SCF, isolated Bands/DOS, and `.wfc*` cleanup [SPEC-03]."""

    def __init__(
        self,
        points_per_segment: int = 30,
        symprec_angstrom: float = 1e-3,
        runner: PWRunnerCallable = default_pw_runner,
    ) -> None:
        self.relaxation_wf = RelaxationWorkflow(runner=runner)
        self.scf_wf = SCFWorkflow(runner=runner)
        self.bands_wf = BandsWorkflow(
            points_per_segment=points_per_segment,
            symprec_angstrom=symprec_angstrom,
            runner=runner,
        )
        self.dos_wf = DOSWorkflow(runner=runner)

    def run(
        self,
        base_dir: Path,
        initial_structure: StructureRecord,
        scf_spec: CalculationSpec,
        bands_spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
        relax_spec: CalculationSpec | None = None,
        dos_spec: CalculationSpec | None = None,
        num_valence_bands: int = 4,
        experimental_ref: ExperimentalGapReference | None = None,
        cleanup_scratch_wfc: bool = True,
    ) -> SemiconductorWorkflowResult:
        """Run full semiconductor pipeline with upstream convergence checks and isolated staging."""
        mat_runs_dir = base_dir / initial_structure.material_id / "runs"

        relax_res: RelaxationWorkflowResult | None = None
        if relax_spec is not None:
            relax_dir = mat_runs_dir / relax_spec.calculation_id
            relax_dir.mkdir(parents=True, exist_ok=True)
            relax_res = self.relaxation_wf.run(
                run_dir=relax_dir,
                structure=initial_structure,
                spec=relax_spec,
                pseudo_sha256=pseudo_sha256,
            )

        scf_dir = mat_runs_dir / scf_spec.calculation_id
        scf_dir.mkdir(parents=True, exist_ok=True)
        scf_res = self.scf_wf.run(
            run_dir=scf_dir,
            initial_structure=initial_structure,
            spec=scf_spec,
            pseudo_sha256=pseudo_sha256,
            relaxation_manifest=relax_res.manifest if relax_res else None,
            relaxed_structure=relax_res.relaxed_structure if relax_res else None,
        )

        bands_dir = mat_runs_dir / bands_spec.calculation_id
        bands_dir.mkdir(parents=True, exist_ok=True)
        bands_res = self.bands_wf.run(
            scf_run_dir=scf_dir,
            scf_manifest=scf_res.manifest,
            bands_run_dir=bands_dir,
            structure=scf_res.structure,
            spec=bands_spec,
            pseudo_sha256=pseudo_sha256,
            num_valence_bands=num_valence_bands,
            experimental_ref=experimental_ref,
        )

        dependent_manifests = [bands_res.manifest]
        dos_res: DOSWorkflowResult | None = None
        if dos_spec is not None:
            dos_dir = mat_runs_dir / dos_spec.calculation_id
            dos_dir.mkdir(parents=True, exist_ok=True)
            dos_res = self.dos_wf.run(
                scf_run_dir=scf_dir,
                scf_manifest=scf_res.manifest,
                dos_run_dir=dos_dir,
                structure=scf_res.structure,
                spec=dos_spec,
                pseudo_sha256=pseudo_sha256,
            )
            dependent_manifests.append(dos_res.manifest)

        cleaned: list[Path] = []
        if cleanup_scratch_wfc:
            cleaned = cleanup_temporary_wavefunctions(scf_dir, dependent_manifests)

        return SemiconductorWorkflowResult(
            relaxation=relax_res,
            scf=scf_res,
            bands=bands_res,
            dos=dos_res,
            cleaned_wavefunction_files=cleaned,
        )
