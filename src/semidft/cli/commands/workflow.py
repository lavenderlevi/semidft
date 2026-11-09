"""CLI subcommands for running multi-step semiconductor DFT workflows."""

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console

from semidft.analysis.validation import load_benchmark_references
from semidft.cli.commands.structure import _resolve_structure
from semidft.core.models import CalculationSpec, CalculationType
from semidft.pseudopotentials.catalog import load_pseudo_catalog
from semidft.pseudopotentials.resolver import resolve_cutoffs
from semidft.pseudopotentials.validator import validate_pseudopotential_set
from semidft.storage.database import ProvenanceDatabase
from semidft.workflows.semiconductor import SemiconductorWorkflow

workflow_app = typer.Typer(help="Orchestrate multi-step semiconductor DFT workflows.")
console = Console()

_PRESET_CONFIG_MAP: dict[str, str] = {
    "silicon-basic": "configs/materials/si.yaml",
    "silicon-relax": "configs/materials/si.yaml",
    "silicon-bands": "configs/materials/si.yaml",
    "silicon-dos": "configs/materials/si.yaml",
    "germanium-basic": "configs/materials/ge.yaml",
    "gaas-basic": "configs/materials/gaas.yaml",
}


def _resolve_workflow_config(target: str) -> tuple[str, dict[str, Any]]:
    path = Path(_PRESET_CONFIG_MAP.get(target, target))
    if not path.is_file():
        raise typer.BadParameter(f"Workflow preset or YAML config not found: {target!r}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return (target, raw)


@workflow_app.command("run")
def cmd_workflow_run(
    target: str = typer.Argument(
        ...,
        help="Workflow preset (e.g. silicon-basic) or path to material YAML config.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate structure, pseudopotentials, and workflow plan without launching QE.",
    ),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    pseudo_dir: Path = typer.Option(  # noqa: B008
        Path("data/pseudopotentials/sssp-pbe-v2"),
        "--pseudo-dir",
        help="Directory containing .UPF files.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Execute or dry-run a semiconductor characterization workflow."""
    wf_name, cfg = _resolve_workflow_config(target)
    mat_section = cfg.get("material", {})
    formula = str(mat_section.get("formula", "Si"))
    struct_source = str(cfg.get("structure", {}).get("source", formula))
    structure = _resolve_structure(struct_source)

    method_section = cfg.get("method", {})
    catalog_path = Path(
        method_section.get("pseudopotentials", {}).get(
            "catalog_path", "configs/pseudopotentials/sssp-pbe.yaml"
        )
    )
    catalog = load_pseudo_catalog(catalog_path)
    validated_pseudos = validate_pseudopotential_set(
        elements=structure.species,
        catalog=catalog,
        pseudo_dir=pseudo_dir if (not dry_run and pseudo_dir.is_dir()) else None,
        require_files=(not dry_run and pseudo_dir.is_dir()),
        expected_xc=str(method_section.get("exchange_correlation", "PBE")),
    )
    ecutwfc_ry, ecutrho_ry = resolve_cutoffs(validated_pseudos)
    pseudo_files = {el: meta.filename for el, meta in validated_pseudos.items()}
    pseudo_hashes = {
        el: meta.sha256 or "catalog_unverified" for el, meta in validated_pseudos.items()
    }

    calcs_cfg = cfg.get("calculations", {})
    steps = ["scf", "bands"]
    if calcs_cfg.get("relaxation", {}).get("enabled", False):
        steps.insert(0, "vc-relax")
    if calcs_cfg.get("dos", {}).get("enabled", False):
        steps.append("dos")

    if dry_run:
        plan_summary: dict[str, Any] = {
            "workflow": wf_name,
            "material_id": structure.material_id,
            "formula": formula,
            "dry_run": True,
            "ecutwfc_ry": ecutwfc_ry,
            "ecutrho_ry": ecutrho_ry,
            "planned_steps": steps,
            "base_dir": str(base_dir),
        }
        if json_output:
            typer.echo(json.dumps(plan_summary, indent=2))
        else:
            console.print_json(data=plan_summary)
        return

    prefix = formula.lower()
    relax_spec: CalculationSpec | None = None
    if "vc-relax" in steps:
        relax_spec = CalculationSpec(
            calculation_id=f"{prefix}-relax-001",
            material_id=structure.material_id,
            calculation_type=CalculationType.VC_RELAX,
            pseudopotentials=pseudo_files,
            ecutwfc_ry=ecutwfc_ry,
            ecutrho_ry=ecutrho_ry,
        )

    scf_spec = CalculationSpec(
        calculation_id=f"{prefix}-scf-001",
        material_id=structure.material_id,
        calculation_type=CalculationType.SCF,
        pseudopotentials=pseudo_files,
        ecutwfc_ry=ecutwfc_ry,
        ecutrho_ry=ecutrho_ry,
    )
    bands_spec = CalculationSpec(
        calculation_id=f"{prefix}-bands-001",
        material_id=structure.material_id,
        calculation_type=CalculationType.BANDS,
        pseudopotentials=pseudo_files,
        ecutwfc_ry=ecutwfc_ry,
        ecutrho_ry=ecutrho_ry,
    )
    dos_spec: CalculationSpec | None = None
    if "dos" in steps:
        dos_spec = CalculationSpec(
            calculation_id=f"{prefix}-dos-001",
            material_id=structure.material_id,
            calculation_type=CalculationType.NSCF,
            pseudopotentials=pseudo_files,
            ecutwfc_ry=ecutwfc_ry,
            ecutrho_ry=ecutrho_ry,
            kpoints=[16, 16, 16],
        )

    benchmarks = load_benchmark_references()
    exp_ref = benchmarks[formula].experimental_gap if formula in benchmarks else None

    wf = SemiconductorWorkflow()
    result = wf.run(
        base_dir=base_dir,
        initial_structure=structure,
        scf_spec=scf_spec,
        bands_spec=bands_spec,
        pseudo_sha256=pseudo_hashes,
        relax_spec=relax_spec,
        dos_spec=dos_spec,
        experimental_ref=exp_ref,
    )
    db = ProvenanceDatabase(base_dir / "index.sqlite")
    mat_runs = base_dir / structure.material_id / "runs"
    if result.relaxation is not None:
        db.upsert_manifest(
            result.relaxation.manifest, mat_runs / result.relaxation.manifest.calculation_id
        )
    db.upsert_manifest(result.scf.manifest, mat_runs / result.scf.manifest.calculation_id)
    db.upsert_manifest(result.bands.manifest, mat_runs / result.bands.manifest.calculation_id)
    if result.dos is not None:
        db.upsert_manifest(result.dos.manifest, mat_runs / result.dos.manifest.calculation_id)

    summary = {
        "workflow": wf_name,
        "scf_status": result.scf.manifest.validation_status.value,
        "bands_status": result.bands.manifest.validation_status.value,
        "fundamental_gap_ev": result.bands.gap_report.fundamental_gap.value_ev,
        "gap_classification": result.bands.gap_report.gap_classification,
    }
    if json_output:
        typer.echo(json.dumps(summary, indent=2))
    else:
        console.print_json(data=summary)
