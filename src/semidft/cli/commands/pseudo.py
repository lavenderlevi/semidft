"""CLI subcommands for pseudopotential inspection, material checking, and validation."""

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from semidft.cli.commands.structure import _resolve_structure
from semidft.core.exceptions import PseudopotentialError
from semidft.pseudopotentials.catalog import load_pseudo_catalog
from semidft.pseudopotentials.resolver import resolve_cutoffs
from semidft.pseudopotentials.validator import validate_pseudopotential_set

pseudo_app = typer.Typer(help="Inspect, validate, and resolve pseudopotentials and cutoffs.")
console = Console()


@pseudo_app.command("inspect")
def cmd_inspect_pseudo(
    element: str = typer.Argument(..., help="Chemical element symbol (e.g. Si, Ge, Ga, As)."),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Inspect pseudopotential metadata and recommended cutoffs for an element."""
    catalog = load_pseudo_catalog(catalog_path)
    if element not in catalog:
        raise typer.BadParameter(f"Element {element!r} not found in catalog {catalog_path}")
    meta = catalog[element]
    if json_output:
        typer.echo(meta.model_dump_json(indent=2))
    else:
        console.print_json(data=meta.model_dump())


@pseudo_app.command("check-material")
def cmd_check_material(
    target: str = typer.Argument(..., help="Material name (Si/Ge/GaAs) or CIF path."),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Check pseudopotential availability and resolve cutoffs for a material."""
    rec = _resolve_structure(target)
    catalog = load_pseudo_catalog(catalog_path)
    validated = validate_pseudopotential_set(
        elements=rec.species,
        catalog=catalog,
        require_files=False,
        expected_xc="PBE",
    )
    wfc_ry, rho_ry = resolve_cutoffs(validated)
    summary: dict[str, Any] = {
        "material": target,
        "material_id": rec.material_id,
        "species": sorted(set(rec.species)),
        "ecutwfc_ry": wfc_ry,
        "ecutrho_ry": rho_ry,
        "pseudopotentials": {k: v.model_dump() for k, v in validated.items()},
    }
    if json_output:
        typer.echo(json.dumps(summary, indent=2))
    else:
        console.print_json(data=summary)


@pseudo_app.command("validate")
def cmd_validate_pseudos(
    elements: str = typer.Option(
        "Si,Ge,Ga,As",
        "--elements",
        help="Comma-separated element symbols to validate.",
    ),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    pseudo_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--pseudo-dir",
        help="Directory containing .UPF files on disk.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Validate pseudopotential metadata, XC consistency, and UPF files on disk."""
    el_list = [e.strip() for e in elements.split(",") if e.strip()]
    catalog = load_pseudo_catalog(catalog_path)
    req_files = pseudo_dir is not None
    try:
        validated = validate_pseudopotential_set(
            elements=el_list,
            catalog=catalog,
            pseudo_dir=pseudo_dir,
            require_files=req_files,
            expected_xc="PBE",
        )
        wfc_ry, rho_ry = resolve_cutoffs(validated)
        payload: dict[str, Any] = {
            "valid": True,
            "elements": sorted(validated.keys()),
            "ecutwfc_ry": wfc_ry,
            "ecutrho_ry": rho_ry,
            "require_files": req_files,
        }
    except PseudopotentialError as exc:
        payload = {"valid": False, "error": str(exc)}
        if json_output:
            typer.echo(json.dumps(payload, indent=2))
        else:
            console.print_json(data=payload)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print_json(data=payload)
