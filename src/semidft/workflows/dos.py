"""Electronic Density of States (`nscf` + `dos.x`) workflow with isolated SCF staging [SPEC-03]."""

import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from semidft.analysis.density_of_states import DOSData, parse_qe_dos_file
from semidft.analysis.visualization import plot_dos
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    RunManifest,
    StructureRecord,
)
from semidft.engines.qe.executable import discover_qe_executables
from semidft.engines.qe.input_generator import generate_dos_x_input
from semidft.storage.staging import stage_scf_reference_data
from semidft.workflows.base import (
    PWRunnerCallable,
    default_pw_runner,
    require_converged_upstream,
)


class DOSWorkflowResult(BaseModel):
    """Result of an electronic Density of States (`nscf` + `dos`) workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: Path
    staged_save_dir: Path
    manifest: RunManifest
    dos_data: DOSData | None = None
    plot_path: Path | None = None


class DOSWorkflow:
    """Stage converged SCF artifacts, run dense-kmesh NSCF/DOS, and parse/plot DOS [SPEC-03]."""

    def __init__(self, runner: PWRunnerCallable = default_pw_runner) -> None:
        self.runner = runner

    def run(
        self,
        scf_run_dir: Path,
        scf_manifest: RunManifest,
        dos_run_dir: Path,
        structure: StructureRecord,
        spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
        dos_file_path: Path | None = None,
        generate_plot: bool = True,
    ) -> DOSWorkflowResult:
        """Stage SCF reference data into `dos_run_dir`, run NSCF, and parse DOS output."""
        require_converged_upstream(scf_manifest, "scf")
        nscf_spec = spec.model_copy(update={"calculation_type": CalculationType.NSCF})
        staged_save = stage_scf_reference_data(
            scf_run_dir=scf_run_dir,
            scf_manifest=scf_manifest,
            target_run_dir=dos_run_dir,
            target_prefix=nscf_spec.calculation_id,
        )

        manifest = self.runner(dos_run_dir, structure, nscf_spec, pseudo_sha256)
        require_converged_upstream(manifest, "nscf")

        candidate_dos = dos_file_path or (dos_run_dir / "output" / "pwscf.dos")
        if (
            not candidate_dos.is_file()
            and self.runner is default_pw_runner
            and (staged_save / "data-file-schema.xml").is_file()
        ):
            qe = discover_qe_executables()
            if qe.dos_path:
                dos_in_path = dos_run_dir / "input" / "dos.in"
                dos_out_path = dos_run_dir / "output" / "dos.out"
                dos_in_text = generate_dos_x_input(
                    prefix=nscf_spec.calculation_id,
                    outdir=(dos_run_dir / "scratch").resolve(),
                    fildos=str(candidate_dos.resolve()),
                )
                dos_in_path.write_text(dos_in_text, encoding="utf-8")
                proc = subprocess.run(
                    [qe.dos_path, "-in", str(dos_in_path.resolve())],
                    cwd=dos_run_dir,
                    capture_output=True,
                    text=True,
                    timeout=180.0,
                    check=False,
                )
                dos_out_path.write_text(proc.stdout, encoding="utf-8")

        dos_data: DOSData | None = None
        plot_path: Path | None = None
        if candidate_dos.is_file():
            dos_data = parse_qe_dos_file(candidate_dos.read_text(encoding="utf-8"))
            if generate_plot and dos_data.energies_ev:
                plot_path = plot_dos(
                    dos_data=dos_data,
                    output_path=dos_run_dir / "analysis" / "dos.png",
                )

        return DOSWorkflowResult(
            run_dir=dos_run_dir,
            staged_save_dir=staged_save,
            manifest=manifest,
            dos_data=dos_data,
            plot_path=plot_path,
        )
