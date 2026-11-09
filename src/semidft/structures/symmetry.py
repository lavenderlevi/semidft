"""Space-group and symmetry analysis using spglib."""

import spglib
from pydantic import BaseModel, ConfigDict

from semidft.core.exceptions import SymmetryAnalysisError
from semidft.core.models import StructureRecord

UNIQUE_SPECIES_TO_Z: dict[str, int] = {
    "H": 1,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "Al": 13,
    "Si": 14,
    "P": 15,
    "Ga": 31,
    "Ge": 32,
    "As": 33,
    "In": 49,
    "Sb": 51,
}


class SymmetryInfo(BaseModel):
    """Symmetry analysis result with explicit tolerance provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    space_group_symbol: str
    space_group_number: int
    hall_symbol: str
    crystal_system: str
    symprec_angstrom: float
    num_symmetry_operations: int


def _crystal_system_from_number(sg_number: int) -> str:
    if 1 <= sg_number <= 2:
        return "triclinic"
    if 3 <= sg_number <= 15:
        return "monoclinic"
    if 16 <= sg_number <= 74:
        return "orthorhombic"
    if 75 <= sg_number <= 142:
        return "tetragonal"
    if 143 <= sg_number <= 167:
        return "trigonal"
    if 168 <= sg_number <= 194:
        return "hexagonal"
    return "cubic"


def structure_to_spglib_cell(
    record: StructureRecord,
) -> tuple[list[list[float]], list[list[float]], list[int], dict[int, str]]:
    """Convert StructureRecord to spglib (lattice, positions, numbers) tuple."""
    unique_symbols = sorted(set(record.species))
    symbol_to_int: dict[str, int] = {}
    int_to_symbol: dict[int, str] = {}
    for idx, sym in enumerate(unique_symbols, start=1):
        z_num = UNIQUE_SPECIES_TO_Z.get(sym, 100 + idx)
        symbol_to_int[sym] = z_num
        int_to_symbol[z_num] = sym

    lattice = [[float(val) for val in row] for row in record.lattice_matrix_angstrom]
    positions = [[float(val) for val in row] for row in record.fractional_coords]
    numbers = [symbol_to_int[sym] for sym in record.species]
    return (lattice, positions, numbers, int_to_symbol)


def analyze_symmetry(
    record: StructureRecord,
    symprec_angstrom: float = 1e-3,
) -> SymmetryInfo:
    """Analyze crystal symmetry via spglib with explicit symprec_angstrom."""
    lattice, positions, numbers, _ = structure_to_spglib_cell(record)
    dataset = spglib.get_symmetry_dataset((lattice, positions, numbers), symprec=symprec_angstrom)
    if dataset is None:
        raise SymmetryAnalysisError(
            f"spglib failed to determine symmetry for {record.material_id} "
            f"at symprec={symprec_angstrom}"
        )

    sg_number = int(dataset.number)
    sg_symbol = str(dataset.international).strip()
    hall = str(dataset.hall).strip()
    n_ops = len(dataset.rotations)

    return SymmetryInfo(
        space_group_symbol=sg_symbol,
        space_group_number=sg_number,
        hall_symbol=hall,
        crystal_system=_crystal_system_from_number(sg_number),
        symprec_angstrom=symprec_angstrom,
        num_symmetry_operations=n_ops,
    )
