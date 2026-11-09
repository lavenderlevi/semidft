"""CLI subcommands for single-calculation init, validation, preparation, execution, and status."""

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from semidft.analysis.high_symmetry_path import generate_high_symmetry_kpath
from semidft.cli.commands.structure import _resolve_structure
from semidft.core.exceptions import SemiDFTError
from semidft.core.hashing import compute_input_hash, compute_structure_hash
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    ExecutionStatus,
    RunManifest,
    StructureRecord,
    ValidationStatus,
)
from semidft.engines.qe.executable import discover_qe_executables
from semidft.engines.qe.input_generator import generate_pw_input
from semidft.engines.qe.runner import execute_pw_calculation
from semidft.pseudopotentials.catalog import load_pseudo_catalog
from semidft.pseudopotentials.resolver import resolve_cutoffs
from semidft.pseudopotentials.validator import validate_pseudopotential_set
from semidft.storage.artifacts import initialize_run_directory, write_checksums_file
from semidft.storage.database import ProvenanceDatabase
from semidft.storage.manifest import load_manifest, save_manifest
from semidft.structures.cif_io import write_cif
from semidft.structures.validator import validate_structure

calc_app = typer.Typer(help="Initialize, validate, prepare, run, and inspect QE calculations.")
console = Console()


def find_run_directory(base_dir: Path, calc_id: str) -> Path:
    """Locate a calculation directory by calculation_id via SQLite index or directory scan."""
    db_path = base_dir / "index.sqlite"
    if db_path.is_file():
        db = ProvenanceDatabase(db_path)
        rec = db.get_manifest_record(calc_id)
        if rec and Path(rec["run_dir"]).is_dir():
            return Path(rec["run_dir"])

    for candidate in base_dir.glob(f"*/runs/{calc_id}"):
        if candidate.is_dir():
            return candidate
    raise typer.BadParameter(f"Calculation {calc_id!r} not found under {base_dir}")


@calc_app.command("init")
def cmd_calc_init(
    target: str = typer.Argument(..., help="Material name (Si/Ge/GaAs) or CIF path."),
    calc_type: CalculationType = typer.Option(  # noqa: B008
        CalculationType.SCF, "--type", help="Calculation type."
    ),
    calc_id: str | None = typer.Option(None, "--calc-id", help="Explicit calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing run directory."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Initialize an isolated calculation directory and manifest."""
    structure = _resolve_structure(target)
    catalog = load_pseudo_catalog(catalog_path)
    validated_pseudos = validate_pseudopotential_set(
        elements=structure.species,
        catalog=catalog,
        require_files=False,
        expected_xc="PBE",
    )
    ecutwfc_ry, ecutrho_ry = resolve_cutoffs(validated_pseudos)

    resolved_id = calc_id or f"{structure.formula.lower()}-{calc_type.value}-001"
    pseudo_files = {el: meta.filename for el, meta in validated_pseudos.items()}
    pseudo_hashes = {
        el: meta.sha256 or "catalog_unverified" for el, meta in validated_pseudos.items()
    }

    spec = CalculationSpec(
        calculation_id=resolved_id,
        material_id=structure.material_id,
        calculation_type=calc_type,
        xc_functional="PBE",
        pseudopotentials=pseudo_files,
        ecutwfc_ry=ecutwfc_ry,
        ecutrho_ry=ecutrho_ry,
    )

    run_dir = initialize_run_directory(
        base_dir=base_dir,
        material_id=structure.material_id,
        calculation_id=resolved_id,
        overwrite=overwrite,
    )
    (run_dir / "input" / "structure.json").write_text(
        structure.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "input" / "spec.json").write_text(
        spec.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    s_hash = compute_structure_hash(structure)
    i_hash = compute_input_hash(
        structure=structure,
        spec=spec,
        pseudo_sha256=pseudo_hashes,
        qe_version="7.5",
    )
    manifest = RunManifest(
        calculation_id=resolved_id,
        material_id=structure.material_id,
        calculation_type=calc_type,
        execution_status=ExecutionStatus.CREATED,
        validation_status=ValidationStatus.NOT_EVALUATED,
        structure_hash=s_hash,
        input_hash=i_hash,
        qe_version="7.5",
        xc_functional=spec.xc_functional,
        ecutwfc_ry=spec.ecutwfc_ry,
        ecutrho_ry=spec.ecutrho_ry,
        kpoints=spec.kpoints,
        pseudo_checksums=pseudo_hashes,
    )
    save_manifest(run_dir, manifest)
    db = ProvenanceDatabase(base_dir / "index.sqlite")
    db.upsert_manifest(manifest, run_dir)

    if json_output:
        typer.echo(manifest.model_dump_json(indent=2))
    else:
        console.print_json(data=manifest.model_dump())


@calc_app.command("validate")
def cmd_calc_validate(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    pseudo_dir: Path | None = typer.Option(  # noqa: B008
        None, "--pseudo-dir", help="Optional directory containing .UPF files."
    ),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Validate structure and pseudopotential inputs for a calculation."""
    run_dir = find_run_directory(base_dir, calc_id)
    structure = StructureRecord.model_validate_json(
        (run_dir / "input" / "structure.json").read_text(encoding="utf-8")
    )
    spec = CalculationSpec.model_validate_json(
        (run_dir / "input" / "spec.json").read_text(encoding="utf-8")
    )
    catalog = load_pseudo_catalog(catalog_path)
    try:
        validate_structure(structure)
        validate_pseudopotential_set(
            elements=structure.species,
            catalog=catalog,
            pseudo_dir=pseudo_dir,
            require_files=pseudo_dir is not None,
            expected_xc=spec.xc_functional,
            spin_orbit=(spec.spin_mode == "noncollinear_soc"),
        )
        payload: dict[str, Any] = {
            "calculation_id": calc_id,
            "valid": True,
            "run_dir": str(run_dir),
        }
    except SemiDFTError as exc:
        payload = {"calculation_id": calc_id, "valid": False, "error": str(exc)}
        if json_output:
            typer.echo(json.dumps(payload, indent=2))
        else:
            console.print_json(data=payload)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print_json(data=payload)


@calc_app.command("prepare")
def cmd_calc_prepare(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    pseudo_dir: Path = typer.Option(  # noqa: B008
        Path("data/pseudopotentials/sssp-pbe-v2"),
        "--pseudo-dir",
        help="Directory containing .UPF files.",
    ),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Generate Quantum ESPRESSO pw.in and update status to PREPARED."""
    run_dir = find_run_directory(base_dir, calc_id)
    structure = StructureRecord.model_validate_json(
        (run_dir / "input" / "structure.json").read_text(encoding="utf-8")
    )
    spec = CalculationSpec.model_validate_json(
        (run_dir / "input" / "spec.json").read_text(encoding="utf-8")
    )
    manifest = load_manifest(run_dir)
    catalog = load_pseudo_catalog(catalog_path)
    validated_pseudos = validate_pseudopotential_set(
        elements=structure.species,
        catalog=catalog,
        pseudo_dir=pseudo_dir if pseudo_dir.is_dir() else None,
        require_files=pseudo_dir.is_dir(),
        expected_xc=spec.xc_functional,
    )
    pseudo_hashes = {
        el: meta.sha256 or manifest.pseudo_checksums.get(el, "unverified")
        for el, meta in validated_pseudos.items()
    }

    kpath_crystal_b: list[tuple[float, float, float, int]] | None = None
    if spec.calculation_type == CalculationType.BANDS:
        structure, kpath = generate_high_symmetry_kpath(structure)
        kpath_crystal_b = [(kx, ky, kz, 1) for kx, ky, kz in kpath.kpoints_fractional]

    input_dir = run_dir / "input"
    write_cif(structure, input_dir / "input_structure.cif")
    pw_in_text = generate_pw_input(
        structure=structure,
        spec=spec,
        pseudo_dir=pseudo_dir,
        outdir=run_dir / "scratch",
        prefix=spec.material_id,
        kpath_crystal_b=kpath_crystal_b,
    )
    pw_in_path = input_dir / "pw.in"
    pw_in_path.write_text(pw_in_text, encoding="utf-8")
    write_checksums_file(run_dir)

    updated = manifest.model_copy(
        update={
            "execution_status": ExecutionStatus.PREPARED,
            "pseudo_checksums": pseudo_hashes,
        }
    )
    save_manifest(run_dir, updated)
    db = ProvenanceDatabase(base_dir / "index.sqlite")
    db.upsert_manifest(updated, run_dir)

    payload = {
        "calculation_id": calc_id,
        "execution_status": updated.execution_status.value,
        "validation_status": updated.validation_status.value,
        "pw_in_path": str(pw_in_path),
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print_json(data=payload)


@calc_app.command("run")
def cmd_calc_run(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    pseudo_dir: Path = typer.Option(  # noqa: B008
        Path("data/pseudopotentials/sssp-pbe-v2"),
        "--pseudo-dir",
        help="Directory containing .UPF files.",
    ),
    catalog_path: Path = typer.Option(  # noqa: B008
        Path("configs/pseudopotentials/sssp-pbe.yaml"),
        "--catalog",
        help="Path to pseudopotential catalog YAML.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Execute a Quantum ESPRESSO calculation and evaluate physical convergence."""
    run_dir = find_run_directory(base_dir, calc_id)
    structure = StructureRecord.model_validate_json(
        (run_dir / "input" / "structure.json").read_text(encoding="utf-8")
    )
    spec = CalculationSpec.model_validate_json(
        (run_dir / "input" / "spec.json").read_text(encoding="utf-8")
    )
    catalog = load_pseudo_catalog(catalog_path)
    validated_pseudos = validate_pseudopotential_set(
        elements=structure.species,
        catalog=catalog,
        pseudo_dir=pseudo_dir,
        require_files=True,
        expected_xc=spec.xc_functional,
    )
    pseudo_hashes = {el: meta.sha256 or "" for el, meta in validated_pseudos.items()}
    qe = discover_qe_executables()
    manifest = execute_pw_calculation(
        run_dir=run_dir,
        structure=structure,
        spec=spec,
        pseudo_sha256=pseudo_hashes,
        pw_executable=qe.pw_path or "pw.x",
        mpirun_executable=qe.mpirun_path,
        qe_version=qe.qe_version or "7.5",
    )
    db = ProvenanceDatabase(base_dir / "index.sqlite")
    db.upsert_manifest(manifest, run_dir)
    if json_output:
        typer.echo(manifest.model_dump_json(indent=2))
    else:
        console.print_json(data=manifest.model_dump())


@calc_app.command("status")
def cmd_calc_status(
    calc_id: str = typer.Argument(..., help="Calculation ID."),
    base_dir: Path = typer.Option(  # noqa: B008
        Path("calculations"), "--base-dir", help="Root calculations directory."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Inspect orthogonal ExecutionStatus and ValidationStatus for a calculation."""
    run_dir = find_run_directory(base_dir, calc_id)
    manifest = load_manifest(run_dir)
    if json_output:
        typer.echo(manifest.model_dump_json(indent=2))
    else:
        console.print_json(data=manifest.model_dump())
