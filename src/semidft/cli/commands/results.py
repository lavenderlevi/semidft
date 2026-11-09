"""CLI subcommands for inspecting calculation energies, band gaps, DOS, and scientific reports."""

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from semidft.analysis.density_of_states import parse_qe_dos_file
from semidft.analysis.gap_classifier import ElectronicGapReport, classify_electronic_gap
from semidft.analysis.report import generate_json_report, generate_markdown_report
from semidft.analysis.validation import (
    load_benchmark_references,
    validate_against_benchmark,
)
from semidft.analysis.visualization import plot_band_structure, plot_dos
from semidft.cli.commands.calculation import find_run_directory
from semidft.engines.qe.output_parser import parse_pw_output
from semidft.storage.manifest import load_manifest

results_app = typer.Typer(
    help="Inspect energies, band gaps, density of states, and generate scientific reports."
)
console = Console()


def _load_or_compute_gap_report(run_dir: Path) -> ElectronicGapReport | None:
    gap_json = run_dir / "output" / "band_gap.json"
    if gap_json.is_file():
        return ElectronicGapReport.model_validate_json(gap_json.read_text(encoding="utf-8"))

    pw_out = run_dir / "output" / "pw.out"
    if pw_out.is_file():
        parsed = parse_pw_output(pw_out.read_text(encoding="utf-8"))
        if parsed.eigenvalues_ev:
            kpts = [(float(i), 0.0, 0.0) for i in range(len(parsed.eigenvalues_ev))]
            return classify_electronic_gap(
                eigenvalues_ev=parsed.eigenvalues_ev,
                kpoints_fractional=kpts,
                num_valence_bands=4,
            )
    return None


@results_app.command("energy")
def cmd_results_energy(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Inspect total energy, Fermi energy, forces, pressure, and convergence status."""
    run_dir = find_run_directory(base_dir, calc_id)
    manifest = load_manifest(run_dir)
    payload: dict[str, Any] = {
        "calculation_id": manifest.calculation_id,
        "material_id": manifest.material_id,
        "execution_status": manifest.execution_status.value,
        "validation_status": manifest.validation_status.value,
        "total_energy_ev": manifest.total_energy_ev,
        "fermi_energy_ev": manifest.fermi_energy_ev,
        "max_force_ev_per_angstrom": manifest.max_force_ev_per_angstrom,
        "pressure_gpa": manifest.pressure_gpa,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print_json(data=payload)


@results_app.command("band-gap")
def cmd_results_band_gap(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Inspect fundamental and direct band gaps and band-edge coordinates."""
    run_dir = find_run_directory(base_dir, calc_id)
    gap_rep = _load_or_compute_gap_report(run_dir)
    if gap_rep is None:
        raise typer.BadParameter(f"No band gap or eigenvalue data found in {run_dir}")
    if json_output:
        typer.echo(gap_rep.model_dump_json(indent=2))
    else:
        console.print_json(data=gap_rep.model_dump())


@results_app.command("bands")
def cmd_results_bands(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    plot_path: Path | None = typer.Option(  # noqa: B008
        None, "--plot", "-o", help="Optional output PNG path for band structure plot."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Summarize and optionally plot electronic band structure."""
    run_dir = find_run_directory(base_dir, calc_id)
    gap_rep = _load_or_compute_gap_report(run_dir)
    if gap_rep is None:
        raise typer.BadParameter(f"No band eigenvalues found in {run_dir}")

    pw_out = run_dir / "output" / "pw.out"
    if plot_path is not None and pw_out.is_file():
        parsed = parse_pw_output(pw_out.read_text(encoding="utf-8"))
        n_k = len(parsed.eigenvalues_ev)
        dists = [float(i) for i in range(n_k)]
        labels: list[str | None] = [None] * n_k
        plot_band_structure(
            distances=dists,
            eigenvalues_ev=parsed.eigenvalues_ev,
            vbm_ev=gap_rep.fundamental_gap.vbm.energy_ev,
            labels=labels,
            output_path=plot_path,
        )

    if json_output:
        typer.echo(gap_rep.model_dump_json(indent=2))
    else:
        console.print_json(data=gap_rep.model_dump())


@results_app.command("dos")
def cmd_results_dos(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    plot_path: Path | None = typer.Option(  # noqa: B008
        None, "--plot", "-o", help="Optional output PNG path for DOS plot."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Parse and optionally plot electronic Density of States."""
    run_dir = find_run_directory(base_dir, calc_id)
    dos_file = run_dir / "output" / "pwscf.dos"
    if not dos_file.is_file():
        raise typer.BadParameter(f"DOS output file not found: {dos_file}")

    dos_data = parse_qe_dos_file(dos_file.read_text(encoding="utf-8"))
    if plot_path is not None:
        plot_dos(dos_data, plot_path)

    if json_output:
        typer.echo(dos_data.model_dump_json(indent=2))
    else:
        console.print_json(data=dos_data.model_dump())


@results_app.command("report")
def cmd_results_report(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Optional path to save Markdown or JSON report."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON report."),
) -> None:
    """Generate a scientific validation report (Markdown or JSON) for a calculation."""
    run_dir = find_run_directory(base_dir, calc_id)
    manifest = load_manifest(run_dir)
    gap_rep = _load_or_compute_gap_report(run_dir)

    benchmarks = load_benchmark_references()
    symbol_map = {
        "silicon-diamond": "Si",
        "germanium-diamond": "Ge",
        "gaas-zincblende": "GaAs",
        "si": "Si",
        "ge": "Ge",
        "gaas": "GaAs",
    }
    sym = symbol_map.get(manifest.material_id.lower())
    val_summary = None
    if sym and sym in benchmarks:
        val_summary = validate_against_benchmark(
            material_symbol=sym,
            computed_a0_angstrom=None,
            computed_b0_gpa=None,
            gap_report=gap_rep,
            benchmark=benchmarks[sym],
        )

    if json_output:
        json_text = generate_json_report(manifest, gap_rep, val_summary)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json_text + "\n", encoding="utf-8")
        typer.echo(json_text)
    else:
        md_text = generate_markdown_report(manifest, gap_rep, val_summary)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(md_text + "\n", encoding="utf-8")
        typer.echo(md_text)
