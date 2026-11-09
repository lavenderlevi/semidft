"""Physical and crystallographic validation for crystal structures."""

import math

import numpy as np
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure

from semidft.core.exceptions import StructureValidationError
from semidft.core.models import StructureRecord


def structure_record_to_pymatgen(record: StructureRecord) -> Structure:
    """Convert a StructureRecord into a pymatgen.core.Structure."""
    lattice = Lattice(record.lattice_matrix_angstrom)
    return Structure(
        lattice=lattice,
        species=record.species,
        coords=record.fractional_coords,
        coords_are_cartesian=False,
    )


def validate_structure(
    record: StructureRecord,
    min_distance_angstrom: float = 0.5,
) -> StructureRecord:
    """Validate finite coordinates, positive cell volume, and interatomic distances."""
    mat = np.asarray(record.lattice_matrix_angstrom, dtype=float)
    coords = np.asarray(record.fractional_coords, dtype=float)

    if not np.all(np.isfinite(mat)) or not np.all(np.isfinite(coords)):
        raise StructureValidationError(
            "Structure contains non-finite lattice or coordinate values."
        )

    det = float(np.linalg.det(mat))
    if det <= 1e-3:
        raise StructureValidationError(
            f"Structure cell volume must be strictly positive (> 1e-3 Å^3), got det={det:.6f}."
        )

    pmg = structure_record_to_pymatgen(record)
    if not pmg.is_ordered:
        raise StructureValidationError(
            "Disordered or partially occupied structures are not supported "
            "without explicit ordering."
        )

    if len(pmg) > 1:
        dist_matrix = np.asarray(pmg.distance_matrix, dtype=float)
        np.fill_diagonal(dist_matrix, math.inf)
        min_dist = float(np.min(dist_matrix))
        if min_dist < min_distance_angstrom:
            raise StructureValidationError(
                f"Interatomic distance {min_dist:.4f} Å is below minimum threshold "
                f"{min_distance_angstrom:.4f} Å (possible duplicate or overlapping sites)."
            )

    return record
