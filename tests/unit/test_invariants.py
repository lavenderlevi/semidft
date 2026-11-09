import math
from typing import Literal

from hypothesis import given, settings
from hypothesis import strategies as st

from semidft.core.hashing import compute_structure_hash
from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure
from semidft.structures.supercell import generate_supercell
from semidft.structures.validator import structure_record_to_pymatgen


@given(
    n1=st.integers(min_value=1, max_value=3),
    n2=st.integers(min_value=1, max_value=3),
    n3=st.integers(min_value=1, max_value=3),
    material=st.sampled_from(["Si", "Ge", "GaAs"]),
)
@settings(max_examples=25, deadline=None)
def test_supercell_volume_atom_count_and_composition_invariants(
    n1: int, n2: int, n3: int, material: Literal["Si", "Ge", "GaAs"]
) -> None:
    base = build_reference_structure(material, cell_type=CellType.PRIMITIVE)
    base_pmg = structure_record_to_pymatgen(base)

    supercell = generate_supercell(base, (n1, n2, n3))
    super_pmg = structure_record_to_pymatgen(supercell)

    det_p = n1 * n2 * n3
    assert len(supercell.species) == det_p * len(base.species)
    assert math.isclose(super_pmg.volume, det_p * base_pmg.volume, rel_tol=1e-9)
    assert super_pmg.composition.reduced_formula == base_pmg.composition.reduced_formula
    assert math.isclose(
        supercell.transformation_history[-1].determinant, float(det_p), rel_tol=1e-9
    )


@given(
    shift_x=st.integers(min_value=-3, max_value=3),
    shift_y=st.integers(min_value=-3, max_value=3),
    shift_z=st.integers(min_value=-3, max_value=3),
)
@settings(max_examples=20, deadline=None)
def test_periodic_coordinate_translation_invariance(
    shift_x: int, shift_y: int, shift_z: int
) -> None:
    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    shifted_coords = [
        [c[0] + shift_x, c[1] + shift_y, c[2] + shift_z] for c in si.fractional_coords
    ]
    si_shifted = si.model_copy(update={"fractional_coords": shifted_coords})
    assert compute_structure_hash(si) == compute_structure_hash(si_shifted)
