from typing import Literal

import pytest

from semidft.core.exceptions import StructureValidationError
from semidft.core.models import StructureRecord
from semidft.structures.builder import build_reference_structure
from semidft.structures.validator import validate_structure


def test_valid_reference_structures_pass() -> None:
    materials: tuple[Literal["Si", "Ge", "GaAs"], ...] = ("Si", "Ge", "GaAs")
    for mat in materials:
        rec = build_reference_structure(mat)
        validated = validate_structure(rec)
        assert validated.material_id == rec.material_id


def test_validator_rejects_overlapping_atoms() -> None:
    overlapping = StructureRecord(
        material_id="si-overlap",
        formula="Si",
        lattice_matrix_angstrom=[
            [5.43, 0.0, 0.0],
            [0.0, 5.43, 0.0],
            [0.0, 0.0, 5.43],
        ],
        species=["Si", "Si"],
        fractional_coords=[[0.0, 0.0, 0.0], [0.01, 0.01, 0.01]],
    )
    with pytest.raises(StructureValidationError, match="Interatomic distance"):
        validate_structure(overlapping, min_distance_angstrom=0.5)


def test_validator_rejects_negative_or_singular_volume() -> None:
    singular = StructureRecord(
        material_id="si-flat",
        formula="Si",
        lattice_matrix_angstrom=[
            [5.43, 0.0, 0.0],
            [5.43, 0.0, 0.0],
            [0.0, 0.0, 5.43],
        ],
        species=["Si"],
        fractional_coords=[[0.0, 0.0, 0.0]],
    )
    with pytest.raises(StructureValidationError, match="volume"):
        validate_structure(singular)
