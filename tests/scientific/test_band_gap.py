"""Tier 4 scientific validation tests for Si, Ge, and GaAs band gap topology [SPEC-05, SPEC-06]."""

import pytest

from semidft.analysis.gap_classifier import classify_electronic_gap
from semidft.analysis.validation import (
    load_benchmark_references,
    validate_against_benchmark,
)


@pytest.mark.scientific
def test_si_ge_gaas_band_gap_topology_and_pbe_benchmark_agreement_spec_05() -> None:
    benchmarks = load_benchmark_references()

    # 1. Silicon: indirect Gamma -> Delta (along Gamma-X), PBE gap ~ 0.58 eV
    si_kpts = [(0.0, 0.0, 0.0), (0.42, 0.0, 0.42), (0.5, 0.5, 0.5)]
    si_eigs = [
        [-6.0, 3.0, 6.00, 6.00, 8.55],
        [-5.0, 2.0, 4.10, 4.20, 6.58],
        [-4.5, 2.5, 4.80, 4.80, 7.45],
    ]
    si_rep = classify_electronic_gap(
        si_eigs,
        si_kpts,
        num_valence_bands=4,
        xc_functional="PBE",
        experimental_ref=benchmarks["Si"].experimental_gap,
    )
    si_val = validate_against_benchmark("Si", None, None, si_rep, benchmarks["Si"])
    assert si_val.pbe_gap_agreed is True
    assert si_val.gap_topology_agreed is True
    assert si_val.experimental_gap_deviation_ev is not None
    assert si_val.experimental_gap_deviation_ev < 0.0

    # 2. Germanium: indirect Gamma -> L, PBE gap ~ 0.11 eV
    ge_kpts = [(0.0, 0.0, 0.0), (0.5, 0.0, 0.5), (0.5, 0.5, 0.5)]
    ge_eigs = [
        [-6.0, 2.5, 5.00, 5.00, 5.45],
        [-5.0, 1.8, 3.50, 3.60, 5.65],
        [-4.5, 2.0, 3.90, 3.90, 5.11],
    ]
    ge_rep = classify_electronic_gap(
        ge_eigs,
        ge_kpts,
        num_valence_bands=4,
        xc_functional="PBE",
        experimental_ref=benchmarks["Ge"].experimental_gap,
    )
    ge_val = validate_against_benchmark("Ge", None, None, ge_rep, benchmarks["Ge"])
    assert ge_val.pbe_gap_agreed is True
    assert ge_val.gap_topology_agreed is True

    # 3. GaAs: direct Gamma -> Gamma, PBE gap ~ 0.52 eV
    gaas_kpts = [(0.0, 0.0, 0.0), (0.5, 0.0, 0.5), (0.5, 0.5, 0.5)]
    gaas_eigs = [
        [-6.5, 2.2, 4.80, 4.80, 5.32],
        [-5.2, 1.5, 3.10, 3.20, 6.40],
        [-4.8, 1.8, 3.60, 3.60, 6.10],
    ]
    gaas_rep = classify_electronic_gap(
        gaas_eigs,
        gaas_kpts,
        num_valence_bands=4,
        xc_functional="PBE",
        experimental_ref=benchmarks["GaAs"].experimental_gap,
    )
    gaas_val = validate_against_benchmark("GaAs", None, None, gaas_rep, benchmarks["GaAs"])
    assert gaas_val.pbe_gap_agreed is True
    assert gaas_val.gap_topology_agreed is True
