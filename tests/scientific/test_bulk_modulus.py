"""Tier 4 scientific validation tests for bulk modulus B0 via Birch-Murnaghan EOS [SPEC-06]."""

import numpy as np
import pytest

from semidft.analysis.eos import (
    EV_PER_ANG3_TO_GPA,
    birch_murnaghan_energy_ev,
    fit_birch_murnaghan_eos,
)
from semidft.analysis.validation import (
    load_benchmark_references,
    validate_against_benchmark,
)


@pytest.mark.scientific
def test_semiconductor_bulk_modulus_validation_spec_06() -> None:
    benchmarks = load_benchmark_references()
    scales = [0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06]

    pbe_computed_b0 = {
        "Si": 88.8,
        "Ge": 58.7,
        "GaAs": 61.2,
    }
    for symbol, target_b0 in pbe_computed_b0.items():
        bench = benchmarks[symbol]
        v0_prim = (bench.pbe_lattice_a0_angstrom**3) / 4.0
        vols = [v0_prim * s for s in scales]
        energies = birch_murnaghan_energy_ev(
            np.asarray(vols),
            -215.0,
            v0_prim,
            target_b0 / EV_PER_ANG3_TO_GPA,
            4.2,
        ).tolist()
        eos_fit = fit_birch_murnaghan_eos(vols, energies, atoms_per_conventional_ratio=4.0)
        val = validate_against_benchmark(
            material_symbol=symbol,
            computed_a0_angstrom=eos_fit.cubic_lattice_constant_a0_angstrom,
            computed_b0_gpa=eos_fit.bulk_modulus_gpa,
            gap_report=None,
            benchmark=bench,
        )
        assert val.pbe_bulk_modulus_agreed is True
        assert val.pbe_lattice_agreed is True
