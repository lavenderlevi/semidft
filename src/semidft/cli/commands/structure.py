"""CLI subcommands for crystal structure import, inspection, symmetry, and standardization."""

import json
from pathlib import Path
from typing import Literal, cast

import typer
from rich.console import Console

from semidft.core.models import CellType, StructureRecord
from semidft.structures.builder import build_reference_structure
from semidft.structures.cif_io import read_cif, write_cif
from semidft.structures.standardization import standardize_structure
from semidft.structures.supercell import generate_supercell
from semidft.structures.symmetry import analyze_symmetry
from semidft.structures.validator import structure_record_to_pymatgen

structure_app = typer.Typer(help="Manage, validate, and transform crystal structures.")
console = Console()


def _resolve_structure(target: str) -> StructureRecord:
    path = Path(target)
    if path.is_file():
        return read_cif(path)
    if target in ("Si", "Ge", "GaAs"):
        mat = cast(Literal["Si", "Ge", "GaAs"], target)
        return build_reference_structure(mat, cell_type=CellType.PRIMITIVE)
    bundled = Path("data/structures") / f"{target}.cif"
    if bundled.is_file():
        return read_cif(bundled)
    raise typer.BadParameter(f"Cannot resolve structure from {target!r}")


@structure_app.command("import")
def cmd_import(
    cif_path: Path = typer.Argument(..., help="Path to input CIF file."),  # noqa: B008
    material_id: str | None = typer.Option(None, "--id", help="Material identifier."),  # noqa: B008
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Optional output JSON path."
    ),
) -> None:
    """Import and validate a CIF file."""
    rec = read_cif(cif_path, material_id=material_id)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rec.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(rec.model_dump_json(indent=2))


@structure_app.command("inspect")
def cmd_inspect(
    target: str = typer.Argument(..., help="Material name (Si/Ge/GaAs) or CIF path."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Inspect crystallographic metadata and cell volume."""
    rec = _resolve_structure(target)
    pmg = structure_record_to_pymatgen(rec)
    sym = analyze_symmetry(rec, symprec_angstrom=rec.symprec_angstrom or 1e-3)
    summary = {
        "material_id": rec.material_id,
        "formula": rec.formula,
        "number_of_atoms": len(rec.species),
        "space_group": sym.space_group_symbol,
        "space_group_number": sym.space_group_number,
        "lattice_type": sym.crystal_system,
        "volume_angstrom3": round(float(pmg.volume), 6),
        "cell_type": rec.cell_type.value,
        "symprec_angstrom": sym.symprec_angstrom,
    }
    if json_output:
        typer.echo(json.dumps(summary, indent=2))
    else:
        console.print_json(data=summary)


@structure_app.command("symmetry")
def cmd_symmetry(
    target: str = typer.Argument(..., help="Material name or CIF path."),
    symprec: float = typer.Option(1e-3, "--symprec", help="Symmetry tolerance in Angstrom."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Determine space group and crystal system via spglib."""
    rec = _resolve_structure(target)
    sym = analyze_symmetry(rec, symprec_angstrom=symprec)
    if json_output:
        typer.echo(sym.model_dump_json(indent=2))
    else:
        console.print_json(data=sym.model_dump())


@structure_app.command("standardize")
def cmd_standardize(
    target: str = typer.Argument(..., help="Material name or CIF path."),
    cell: Literal["primitive", "conventional"] = typer.Option("primitive", "--cell"),
    symprec: float = typer.Option(1e-3, "--symprec"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output CIF path."),  # noqa: B008
) -> None:
    """Standardize a structure to primitive or conventional cell."""
    rec = _resolve_structure(target)
    std = standardize_structure(rec, target=cell, symprec_angstrom=symprec)
    if output:
        write_cif(std, output)
    typer.echo(std.model_dump_json(indent=2))


@structure_app.command("supercell")
def cmd_supercell(
    target: str = typer.Argument(..., help="Material name or CIF path."),
    matrix: tuple[int, int, int] = typer.Option(
        (2, 2, 2), "--matrix", help="Diagonal scaling N1 N2 N3."
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output CIF path."),  # noqa: B008
) -> None:
    """Generate a supercell from a diagonal scaling tuple."""
    rec = _resolve_structure(target)
    sc = generate_supercell(rec, matrix)
    if output:
        write_cif(sc, output)
    typer.echo(sc.model_dump_json(indent=2))
