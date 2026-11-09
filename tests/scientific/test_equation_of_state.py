"""Tier 4 scientific validation tests for 3rd-order Birch-Murnaghan EOS on Si, Ge, GaAs."""

import math

import numpy as np
import pytest

from semidft.analysis.eos import (
    EV_PER_ANG3_TO_GPA,
    birch_murnaghan_energy_ev,
    fit_birch_murnaghan_eos,
)
from semidft.analysis.validation import load_benchmark_references


@pytest.mark.scientific
def test_birch_murnaghan_eos_equilibrium_volumes_for_si_ge_gaas() -> None:
    benchmarks = load_benchmark_references()
    scales = [0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06]

    for symbol in ("Si", "Ge", "GaAs"):
        bench = benchmarks[symbol]
        v0_prim = (bench.pbe_lattice_a0_angstrom**3) / 4.0
        b0_ev_ang3 = bench.pbe_bulk_modulus_gpa / EV_PER_ANG3_TO_GPA
        vols = [v0_prim * s for s in scales]
        energies = birch_murnaghan_energy_ev(
            np.asarray(vols), -200.0, v0_prim, b0_ev_ang3, 4.35
        ).tolist()

        res = fit_birch_murnaghan_eos(vols, energies, atoms_per_conventional_ratio=4.0)
        assert math.isclose(
            res.cubic_lattice_constant_a0_angstrom,
            bench.pbe_lattice_a0_angstrom,
            abs_tol=bench.pbe_lattice_tolerance_angstrom,
        )
        assert res.rmse_ev < 1e-6
