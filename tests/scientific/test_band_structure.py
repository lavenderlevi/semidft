"""Tier 4 scientific validation tests for coordinate-consistent high-symmetry paths [SPEC-04]."""

import pytest

from semidft.analysis.high_symmetry_path import generate_high_symmetry_kpath
from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure


@pytest.mark.scientific
def test_fcc_high_symmetry_kpath_for_si_ge_gaas_spec_04() -> None:
    for symbol in ("Si", "Ge", "GaAs"):
        conv = build_reference_structure(symbol, cell_type=CellType.CONVENTIONAL)
        std_prim, kpath = generate_high_symmetry_kpath(conv, points_per_segment=20)
        assert std_prim.cell_type == CellType.PRIMITIVE
        assert len(std_prim.species) == 2
        for hs_label in ("GAMMA", "X", "L"):
            assert hs_label in kpath.high_symmetry_points
        assert len(kpath.kpoints_fractional) == len(kpath.kpoints_linear_distance)
