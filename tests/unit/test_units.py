import math

import pytest

from semidft.core.exceptions import (
    ConvergenceError,
    PseudopotentialError,
    QEConfigurationError,
    SemiDFTError,
    StructureValidationError,
)
from semidft.core.units import (
    BOHR_TO_ANGSTROM,
    GPA_TO_KBAR,
    KBAR_TO_GPA,
    RY_PER_BOHR_TO_EV_PER_ANGSTROM,
    RY_TO_EV,
    angstrom_to_bohr,
    bohr_to_angstrom,
    energy_ev_to_etot_conv_thr_ry,
    ev_per_angstrom_to_ry_per_bohr,
    ev_to_ry,
    force_ev_ang_to_forc_conv_thr_ry_bohr,
    gpa_to_kbar,
    kbar_to_gpa,
    pressure_gpa_to_press_conv_thr_kbar,
    ry_per_bohr_to_ev_per_angstrom,
    ry_to_ev,
)


def test_codata_constants_and_round_trips() -> None:
    assert math.isclose(RY_TO_EV, 13.605693122994, rel_tol=1e-12)
    assert math.isclose(BOHR_TO_ANGSTROM, 0.529177210903, rel_tol=1e-12)
    # Exact CODATA 2018/2022 ratio: 13.605693122994 / 0.529177210903 = 25.711033738162943
    assert math.isclose(RY_PER_BOHR_TO_EV_PER_ANGSTROM, 25.711033738162943, rel_tol=1e-12)
    assert math.isclose(GPA_TO_KBAR, 10.0, rel_tol=1e-12)
    assert math.isclose(KBAR_TO_GPA, 0.1, rel_tol=1e-12)

    assert math.isclose(ev_to_ry(ry_to_ev(45.0)), 45.0, rel_tol=1e-12)
    assert math.isclose(angstrom_to_bohr(bohr_to_angstrom(10.26)), 10.26, rel_tol=1e-12)
    assert math.isclose(
        ev_per_angstrom_to_ry_per_bohr(ry_per_bohr_to_ev_per_angstrom(1e-3)),
        1e-3,
        rel_tol=1e-12,
    )
    assert math.isclose(gpa_to_kbar(kbar_to_gpa(5.0)), 5.0, rel_tol=1e-12)


def test_qe_convergence_threshold_conversions_spec_02() -> None:
    etot_ry = energy_ev_to_etot_conv_thr_ry(1.3605693122994e-3)
    assert math.isclose(etot_ry, 1.0e-4, rel_tol=1e-10)

    forc_ry_bohr = force_ev_ang_to_forc_conv_thr_ry_bohr(0.01)
    assert math.isclose(forc_ry_bohr, 0.01 / 25.711033738162943, rel_tol=1e-12)

    press_kbar = pressure_gpa_to_press_conv_thr_kbar(0.05)
    assert math.isclose(press_kbar, 0.5, rel_tol=1e-12)


def test_threshold_conversions_reject_non_positive_values() -> None:
    with pytest.raises(ValueError, match="must be strictly positive"):
        energy_ev_to_etot_conv_thr_ry(0.0)
    with pytest.raises(ValueError, match="must be strictly positive"):
        force_ev_ang_to_forc_conv_thr_ry_bohr(-0.01)
    with pytest.raises(ValueError, match="must be strictly positive"):
        pressure_gpa_to_press_conv_thr_kbar(0.0)


def test_exception_hierarchy() -> None:
    assert issubclass(StructureValidationError, SemiDFTError)
    assert issubclass(PseudopotentialError, SemiDFTError)
    assert issubclass(QEConfigurationError, SemiDFTError)
    assert issubclass(ConvergenceError, SemiDFTError)
