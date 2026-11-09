"""Reference crystal structure builders for Si, Ge, and GaAs."""

from typing import Literal

from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure

from semidft.core.models import CellType, StructureRecord

REFERENCE_LATTICE_A_ANGSTROM: dict[str, float] = {
    "Si": 5.4309,
    "Ge": 5.6578,
    "GaAs": 5.6532,
}


def build_reference_structure(
    material: Literal["Si", "Ge", "GaAs"],
    cell_type: CellType = CellType.PRIMITIVE,
) -> StructureRecord:
    """Build a canonical diamond/zincblende structure for Si, Ge, or GaAs."""
    if material not in REFERENCE_LATTICE_A_ANGSTROM:
        raise ValueError(f"Unsupported reference material: {material!r}")

    a0 = REFERENCE_LATTICE_A_ANGSTROM[material]
    half = a0 / 2.0
    species_pair: list[str] = ["Ga", "As"] if material == "GaAs" else [str(material), str(material)]
    sg_symbol = "F-43m" if material == "GaAs" else "Fd-3m"
    sg_number = 216 if material == "GaAs" else 227

    if cell_type == CellType.PRIMITIVE:
        lattice = [
            [0.0, half, half],
            [half, 0.0, half],
            [half, half, 0.0],
        ]
        species: list[str] = list(species_pair)
        coords: list[list[float]] = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]
    elif cell_type == CellType.CONVENTIONAL:
        lattice = [
            [a0, 0.0, 0.0],
            [0.0, a0, 0.0],
            [0.0, 0.0, a0],
        ]
        fcc_shifts = [
            [0.0, 0.0, 0.0],
            [0.0, 0.5, 0.5],
            [0.5, 0.0, 0.5],
            [0.5, 0.5, 0.0],
        ]
        species = []
        coords = []
        for shift in fcc_shifts:
            species.append(species_pair[0])
            coords.append([shift[0], shift[1], shift[2]])
            species.append(species_pair[1])
            coords.append([shift[0] + 0.25, shift[1] + 0.25, shift[2] + 0.25])
    else:
        raise ValueError(
            f"build_reference_structure supports PRIMITIVE or CONVENTIONAL, got {cell_type}"
        )

    pmg = Structure(Lattice(lattice), species, coords)
    return StructureRecord(
        material_id=f"{material.lower()}-reference",
        formula=pmg.composition.reduced_formula,
        lattice_matrix_angstrom=lattice,
        species=species,
        fractional_coords=coords,
        space_group_symbol=sg_symbol,
        space_group_number=sg_number,
        symprec_angstrom=1e-3,
        cell_type=cell_type,
    )
