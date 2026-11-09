"""CIF reader/writer and ASE adapter preserving crystallographic invariants."""

from pathlib import Path

from ase import Atoms
from pymatgen.core.structure import Structure
from pymatgen.io.cif import CifParser, CifWriter

from semidft.core.exceptions import StructureValidationError
from semidft.core.models import CellType, StructureRecord
from semidft.structures.validator import (
    structure_record_to_pymatgen,
    validate_structure,
)


def pymatgen_to_structure_record(
    structure: Structure,
    material_id: str,
    cell_type: CellType = CellType.ORIGINAL,
    source_file: str | None = None,
) -> StructureRecord:
    """Convert a validated ordered pymatgen Structure into a StructureRecord."""
    if not structure.is_ordered:
        raise StructureValidationError(
            "Disordered or partially occupied CIF structures are rejected "
            "by policy [AGENTS.md §6.2]."
        )
    lattice_matrix = [[float(val) for val in row] for row in structure.lattice.matrix.tolist()]
    species = [str(site.specie.symbol) for site in structure.sites]
    frac_coords = [
        [float(val) % 1.0 for val in site.frac_coords.tolist()] for site in structure.sites
    ]
    return StructureRecord(
        material_id=material_id,
        formula=structure.composition.reduced_formula,
        lattice_matrix_angstrom=lattice_matrix,
        species=species,
        fractional_coords=frac_coords,
        cell_type=cell_type,
        source_file=source_file,
        source_format="cif",
    )


def read_cif(path: Path, material_id: str | None = None) -> StructureRecord:
    """Read and validate a crystal structure from a CIF file without implicit reduction."""
    if not path.is_file():
        raise StructureValidationError(f"CIF file not found: {path}")

    try:
        parser = CifParser(str(path), occupancy_tolerance=1.0)
        structures = parser.parse_structures(primitive=False, check_occu=True)
    except Exception as exc:
        raise StructureValidationError(
            f"Disordered or partially occupied or malformed CIF in {path.name}: {exc}"
        ) from exc

    if not structures:
        raise StructureValidationError(f"No valid crystal structures found in {path}")

    pmg_struct = structures[0]
    if not pmg_struct.is_ordered:
        raise StructureValidationError(
            f"Disordered or partially occupied sites detected in {path.name}."
        )

    mat_id = material_id or path.stem.lower()
    record = pymatgen_to_structure_record(
        pmg_struct,
        material_id=mat_id,
        cell_type=CellType.ORIGINAL,
        source_file=str(path),
    )
    return validate_structure(record)


def write_cif(record: StructureRecord, path: Path) -> Path:
    """Write a StructureRecord to a CIF file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pmg = structure_record_to_pymatgen(record)
    writer = CifWriter(pmg)
    writer.write_file(str(path))
    return path


def structure_record_to_ase(record: StructureRecord) -> Atoms:
    """Convert a StructureRecord to an ASE Atoms object at the QE adapter boundary."""
    return Atoms(
        symbols=record.species,
        scaled_positions=record.fractional_coords,
        cell=record.lattice_matrix_angstrom,
        pbc=(True, True, True),
    )
