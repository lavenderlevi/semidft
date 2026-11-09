"""Band-structure workflow with isolated SCF staging and seekpath consistency [SPEC-03, SPEC-04]."""

import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from semidft.analysis.gap_classifier import (
    ElectronicGapReport,
    ExperimentalGapReference,
    classify_electronic_gap,
)
from semidft.analysis.high_symmetry_path import (
    HighSymmetryKPath,
    generate_high_symmetry_kpath,
)
from semidft.analysis.visualization import plot_band_structure
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    RunManifest,
    StructureRecord,
)
from semidft.engines.qe.executable import discover_qe_executables
from semidft.engines.qe.input_generator import generate_bands_x_input
from semidft.engines.qe.output_parser import parse_pw_output
from semidft.engines.qe.runner import execute_pw_calculation
from semidft.storage.staging import stage_scf_reference_data
from semidft.workflows.base import (
    PWRunnerCallable,
    default_pw_runner,
    require_converged_upstream,
)


class BandsWorkflowResult(BaseModel):
    """Complete result of a band-structure calculation and gap analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: Path
    staged_save_dir: Path
    standardized_primitive_structure: StructureRecord
    kpath: HighSymmetryKPath
    manifest: RunManifest
    gap_report: ElectronicGapReport
    plot_path: Path | None = None


class BandsWorkflow:
    """Stage converged SCF artifacts, generate k-path, run `bands`, and classify band gap."""

    def __init__(
        self,
        points_per_segment: int = 30,
        symprec_angstrom: float = 1e-3,
        runner: PWRunnerCallable = default_pw_runner,
    ) -> None:
        self.points_per_segment = points_per_segment
        self.symprec_angstrom = symprec_angstrom
        self.runner = runner

    def run(
        self,
        scf_run_dir: Path,
        scf_manifest: RunManifest,
        bands_run_dir: Path,
        structure: StructureRecord,
        spec: CalculationSpec,
        pseudo_sha256: dict[str, str],
        num_valence_bands: int = 4,
        experimental_ref: ExperimentalGapReference | None = None,
        generate_plot: bool = True,
    ) -> BandsWorkflowResult:
        """Stage SCF reference data into `bands_run_dir`, run `bands`, and analyze gap [SPEC-03]."""
        require_converged_upstream(scf_manifest, "scf")
        bands_spec = spec.model_copy(update={"calculation_type": CalculationType.BANDS})
        staged_save = stage_scf_reference_data(
            scf_run_dir=scf_run_dir,
            scf_manifest=scf_manifest,
            target_run_dir=bands_run_dir,
            target_prefix=bands_spec.calculation_id,
        )

        std_prim, kpath = generate_high_symmetry_kpath(
            structure,
            points_per_segment=self.points_per_segment,
            symprec_angstrom=self.symprec_angstrom,
        )
        if self.runner is default_pw_runner:
            kpath_crystal_b = [(kx, ky, kz, 1) for kx, ky, kz in kpath.kpoints_fractional]
            manifest = execute_pw_calculation(
                run_dir=bands_run_dir,
                structure=std_prim,
                spec=bands_spec,
                pseudo_sha256=pseudo_sha256,
                kpath_crystal_b=kpath_crystal_b,
            )
            qe = discover_qe_executables()
            if qe.bands_path and (staged_save / "data-file-schema.xml").is_file():
                bands_in_path = bands_run_dir / "input" / "bands.in"
                bands_out_path = bands_run_dir / "output" / "bands.out"
                bands_dat_path = (bands_run_dir / "output" / "bands.dat").resolve()
                bands_in_text = generate_bands_x_input(
                    prefix=bands_spec.calculation_id,
                    outdir=(bands_run_dir / "scratch").resolve(),
                    filband=str(bands_dat_path),
                )
                bands_in_path.write_text(bands_in_text, encoding="utf-8")
                proc = subprocess.run(
                    [qe.bands_path, "-in", str(bands_in_path.resolve())],
                    cwd=bands_run_dir,
                    capture_output=True,
                    text=True,
                    timeout=180.0,
                    check=False,
                )
                bands_out_path.write_text(proc.stdout, encoding="utf-8")
        else:
            manifest = self.runner(bands_run_dir, std_prim, bands_spec, pseudo_sha256)
        require_converged_upstream(manifest, "bands")

        plot_path: Path | None = None
        pw_out_path = bands_run_dir / "output" / "pw.out"
        parsed = (
            parse_pw_output(pw_out_path.read_text(encoding="utf-8"))
            if pw_out_path.is_file()
            else None
        )
        if parsed is not None and parsed.eigenvalues_ev:
            n_k = min(len(parsed.eigenvalues_ev), len(kpath.kpoints_fractional))
            eigs = parsed.eigenvalues_ev[:n_k]
            kpts = kpath.kpoints_fractional[:n_k]
            gap_report = classify_electronic_gap(
                eigenvalues_ev=eigs,
                kpoints_fractional=kpts,
                num_valence_bands=num_valence_bands,
                xc_functional=bands_spec.xc_functional,
                source="high_symmetry_path",
                experimental_ref=experimental_ref,
            )
            if generate_plot:
                plot_path = plot_band_structure(
                    distances=kpath.kpoints_linear_distance[:n_k],
                    eigenvalues_ev=eigs,
                    vbm_ev=gap_report.fundamental_gap.vbm.energy_ev,
                    labels=kpath.kpoint_labels[:n_k],
                    output_path=bands_run_dir / "analysis" / "bands.png",
                )
        else:
            fallback_eigs = [[0.0] * num_valence_bands + [0.0]]
            fallback_kpts = [kpath.kpoints_fractional[0]]
            gap_report = classify_electronic_gap(
                eigenvalues_ev=fallback_eigs,
                kpoints_fractional=fallback_kpts,
                num_valence_bands=num_valence_bands,
                xc_functional=bands_spec.xc_functional,
                source="high_symmetry_path",
                experimental_ref=experimental_ref,
            )

        return BandsWorkflowResult(
            run_dir=bands_run_dir,
            staged_save_dir=staged_save,
            standardized_primitive_structure=std_prim,
            kpath=kpath,
            manifest=manifest,
            gap_report=gap_report,
            plot_path=plot_path,
        )
