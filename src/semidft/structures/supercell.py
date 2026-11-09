"""Supercell generation with exact transformation matrix and volume invariant checks."""

import numpy as np

from semidft.core.exceptions import StructureValidationError
from semidft.core.models import CellType, StructureRecord, TransformationStep
from semidft.structures.validator import (
    structure_record_to_pymatgen,
    validate_structure,
)


def generate_supercell(
    record: StructureRecord,
    scaling_matrix: list[list[int]] | tuple[int, int, int],
) -> StructureRecord:
    """Create a supercell from a 3-tuple (N1, N2, N3) or 3x3 integer matrix."""
    if isinstance(scaling_matrix, tuple):
        if len(scaling_matrix) != 3 or any(n <= 0 for n in scaling_matrix):
            raise StructureValidationError("Supercell tuple must contain 3 positive integers.")
        mat = [
            [int(scaling_matrix[0]), 0, 0],
            [0, int(scaling_matrix[1]), 0],
            [0, 0, int(scaling_matrix[2])],
        ]
    else:
        mat = [[int(v) for v in row] for row in scaling_matrix]

    det = float(np.linalg.det(np.asarray(mat, dtype=float)))
    if det <= 0.0:
        raise StructureValidationError(f"Supercell matrix determinant must be > 0, got {det}")

    pmg = structure_record_to_pymatgen(record)
    pmg.make_supercell(mat)

    step = TransformationStep(
        operation="supercell",
        transformation_matrix=[[float(v) for v in row] for row in mat],
        determinant=round(det, 8),
        symprec_angstrom=record.symprec_angstrom,
    )
    new_record = StructureRecord(
        material_id=f"{record.material_id}-supercell",
        formula=pmg.composition.reduced_formula,
        lattice_matrix_angstrom=[[float(v) for v in row] for row in pmg.lattice.matrix.tolist()],
        species=[str(site.specie.symbol) for site in pmg.sites],
        fractional_coords=[
            [float(v) % 1.0 for v in site.frac_coords.tolist()] for site in pmg.sites
        ],
        space_group_symbol=record.space_group_symbol,
        space_group_number=record.space_group_number,
        symprec_angstrom=record.symprec_angstrom,
        cell_type=CellType.SUPERCELL,
        source_file=record.source_file,
        source_format=record.source_format,
        transformation_history=[*record.transformation_history, step],
    )
    return validate_structure(new_record)
