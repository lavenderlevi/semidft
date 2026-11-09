"""Primitive and conventional cell standardization with transformation tracking."""

from typing import Literal

import numpy as np
import spglib

from semidft.core.exceptions import SymmetryAnalysisError
from semidft.core.models import CellType, StructureRecord, TransformationStep
from semidft.structures.symmetry import analyze_symmetry, structure_to_spglib_cell
from semidft.structures.validator import validate_structure


def standardize_structure(
    record: StructureRecord,
    target: Literal["primitive", "conventional"] = "primitive",
    symprec_angstrom: float = 1e-3,
) -> StructureRecord:
    """Standardize a structure to its primitive or conventional cell via spglib."""
    lattice, positions, numbers, int_to_symbol = structure_to_spglib_cell(record)
    to_primitive = target == "primitive"

    std_cell = spglib.standardize_cell(
        (lattice, positions, numbers),
        to_primitive=to_primitive,
        no_idealize=False,
        symprec=symprec_angstrom,
    )
    if std_cell is None:
        raise SymmetryAnalysisError(
            f"spglib.standardize_cell failed for {record.material_id} (target={target})"
        )

    new_lattice, new_positions, new_numbers = std_cell
    old_inv = np.linalg.inv(np.asarray(lattice, dtype=float))
    transform_matrix = np.matmul(np.asarray(new_lattice, dtype=float), old_inv)
    det = float(np.linalg.det(transform_matrix))

    sym_info = analyze_symmetry(record, symprec_angstrom=symprec_angstrom)
    step = TransformationStep(
        operation=f"standardize_{target}",
        transformation_matrix=[[float(v) for v in row] for row in transform_matrix.tolist()],
        determinant=det,
        symprec_angstrom=symprec_angstrom,
    )

    new_species = [int_to_symbol[int(num)] for num in new_numbers]
    new_coords = [[float(v) % 1.0 for v in row] for row in new_positions]
    new_record = StructureRecord(
        material_id=record.material_id,
        formula=record.formula,
        lattice_matrix_angstrom=[[float(v) for v in row] for row in new_lattice],
        species=new_species,
        fractional_coords=new_coords,
        space_group_symbol=sym_info.space_group_symbol,
        space_group_number=sym_info.space_group_number,
        symprec_angstrom=symprec_angstrom,
        cell_type=CellType.PRIMITIVE if to_primitive else CellType.CONVENTIONAL,
        source_file=record.source_file,
        source_format=record.source_format,
        transformation_history=[*record.transformation_history, step],
    )
    return validate_structure(new_record)
