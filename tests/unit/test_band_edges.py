import math

from semidft.analysis.gap_classifier import (
    ExperimentalGapReference,
    ExperimentalGapSource,
    classify_electronic_gap,
)
from semidft.analysis.high_symmetry_path import generate_high_symmetry_kpath
from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure


def test_seekpath_enforces_standardized_primitive_cell_consistency_spec_04() -> None:
    si_conv = build_reference_structure("Si", cell_type=CellType.CONVENTIONAL)
    std_prim, kpath = generate_high_symmetry_kpath(si_conv, points_per_segment=15)

    assert len(std_prim.species) == 2
    assert std_prim.cell_type == CellType.PRIMITIVE
    assert "GAMMA" in kpath.high_symmetry_points
    assert "X" in kpath.high_symmetry_points
    assert len(kpath.kpoints_fractional) > 20


def test_gap_classifier_identifies_silicon_indirect_gamma_to_x_spec_05() -> None:
    # 4 valence bands; kpoints: Gamma (0,0,0), Delta (0.42,0,0.42), L (0.5,0.5,0.5)
    kpts = [
        (0.0, 0.0, 0.0),
        (0.42, 0.0, 0.42),
        (0.5, 0.5, 0.5),
    ]
    # Bands 0..3 are valence (VBM = 6.00 eV at Gamma); Band 4 is conduction (CBM = 6.56 eV at Delta)
    eigs = [
        [
            -6.0,
            3.0,
            6.00,
            6.00,
            8.55,
            9.20,
        ],  # Gamma: direct gap = 8.55 - 6.00 = 2.55 eV
        [-5.0, 2.0, 4.10, 4.20, 6.56, 8.10],  # near X: CBM = 6.56 eV
        [-4.5, 2.5, 4.80, 4.80, 7.40, 8.90],  # L
    ]
    exp_ref = ExperimentalGapReference(
        value_ev=1.12,
        temperature_k=300.0,
        phase="diamond-cubic",
        gap_definition="fundamental_electronic",
        uncertainty_ev=0.01,
        source=ExperimentalGapSource(
            doi="10.1063/1.1368156",
            citation="Vurgaftman et al., J. Appl. Phys. 89, 5815 (2001)",
        ),
    )
    report = classify_electronic_gap(
        eigenvalues_ev=eigs,
        kpoints_fractional=kpts,
        num_valence_bands=4,
        xc_functional="PBE",
        source="dense_kmesh",
        dense_kmesh_shape=[16, 16, 16],
        experimental_ref=exp_ref,
    )
    assert report.gap_classification == "indirect"
    assert math.isclose(report.fundamental_gap.value_ev, 0.56, rel_tol=1e-9)
    assert report.fundamental_gap.vbm.kpoint_fractional == (0.0, 0.0, 0.0)
    assert report.fundamental_gap.cbm.kpoint_fractional == (0.42, 0.0, 0.42)
    assert math.isclose(report.minimum_direct_gap.value_ev, 2.36, rel_tol=1e-9)
    assert report.experimental_reference_gap is not None
    assert report.experimental_reference_gap.temperature_k == 300.0


def test_gap_classifier_identifies_ge_indirect_gamma_to_l_and_gaas_direct_spec_05() -> None:
    kpts = [
        (0.0, 0.0, 0.0),
        (0.5, 0.5, 0.5),
        (1.0, 0.0, 0.0),
    ]  # (1,0,0) is equivalent to Gamma modulo Z^3
    # Ge: VBM at Gamma (5.0 eV), CBM at L (5.35 eV)
    ge_eigs = [
        [-5.0, 2.0, 5.00, 5.00, 5.60],
        [-4.0, 1.5, 3.80, 3.80, 5.35],
        [-5.0, 2.0, 5.00, 5.00, 5.60],
    ]
    ge_rep = classify_electronic_gap(ge_eigs, kpts, num_valence_bands=4)
    assert ge_rep.gap_classification == "indirect"
    assert ge_rep.fundamental_gap.cbm.kpoint_fractional == (0.5, 0.5, 0.5)

    # GaAs: VBM at Gamma (5.0 eV), CBM at periodic image (1,0,0) equiv to Gamma (5.52 eV)
    gaas_eigs = [
        [-6.0, 2.0, 5.00, 5.00, 5.52],
        [-5.0, 1.5, 3.80, 3.80, 6.20],
        [-6.0, 2.0, 5.00, 5.00, 5.52],
    ]
    gaas_rep = classify_electronic_gap(gaas_eigs, kpts, num_valence_bands=4)
    assert gaas_rep.gap_classification == "direct"
    assert math.isclose(gaas_rep.fundamental_gap.value_ev, 0.52, rel_tol=1e-9)
