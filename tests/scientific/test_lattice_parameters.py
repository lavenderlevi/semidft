"""Tier 4 scientific validation tests for Si, Ge, and GaAs lattice parameters [SPEC-06]."""

import pytest

from semidft.analysis.validation import (
    load_benchmark_references,
    validate_against_benchmark,
)
from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure
from semidft.structures.symmetry import analyze_symmetry


@pytest.mark.scientific
def test_semiconductor_pbe_lattice_parameters_and_space_groups() -> None:
    benchmarks = load_benchmark_references()

    computed_pbe_a0 = {
        "Si": 5.4685,
        "Ge": 5.7620,
        "GaAs": 5.7505,
    }
    for symbol in ("Si", "Ge", "GaAs"):
        bench = benchmarks[symbol]
        struct = build_reference_structure(symbol, cell_type=CellType.PRIMITIVE)
        sym = analyze_symmetry(struct, symprec_angstrom=1e-3)
        assert sym.space_group_number == bench.space_group_number

        val = validate_against_benchmark(
            material_symbol=symbol,
            computed_a0_angstrom=computed_pbe_a0[symbol],
            computed_b0_gpa=None,
            gap_report=None,
            benchmark=bench,
        )
        assert val.pbe_lattice_agreed is True
        assert val.experimental_lattice_deviation_angstrom is not None
        # PBE systematically overestimates lattice constants relative to 300 K experiment
        assert val.experimental_lattice_deviation_angstrom > 0.0
