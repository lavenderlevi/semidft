"""Centralized physical constants and unit conversions (CODATA 2018/2022)."""

import math

RY_TO_EV: float = 13.605693122994
EV_TO_RY: float = 1.0 / RY_TO_EV

BOHR_TO_ANGSTROM: float = 0.529177210903
ANGSTROM_TO_BOHR: float = 1.0 / BOHR_TO_ANGSTROM

RY_PER_BOHR_TO_EV_PER_ANGSTROM: float = RY_TO_EV / BOHR_TO_ANGSTROM
EV_PER_ANGSTROM_TO_RY_PER_BOHR: float = BOHR_TO_ANGSTROM / RY_TO_EV

GPA_TO_KBAR: float = 10.0
KBAR_TO_GPA: float = 0.1


def _require_finite_positive(value: float, name: str) -> float:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be strictly positive and finite, got {value!r}")
    return float(value)


def ry_to_ev(val_ry: float) -> float:
    """Convert energy from Rydberg (Ry) to electronvolts (eV)."""
    return float(val_ry) * RY_TO_EV


def ev_to_ry(val_ev: float) -> float:
    """Convert energy from electronvolts (eV) to Rydberg (Ry)."""
    return float(val_ev) * EV_TO_RY


def bohr_to_angstrom(val_bohr: float) -> float:
    """Convert length from Bohr radii to Angstroms (Å)."""
    return float(val_bohr) * BOHR_TO_ANGSTROM


def angstrom_to_bohr(val_ang: float) -> float:
    """Convert length from Angstroms (Å) to Bohr radii."""
    return float(val_ang) * ANGSTROM_TO_BOHR


def ry_per_bohr_to_ev_per_angstrom(val_ry_bohr: float) -> float:
    """Convert atomic force from Ry/Bohr to eV/Å."""
    return float(val_ry_bohr) * RY_PER_BOHR_TO_EV_PER_ANGSTROM


def ev_per_angstrom_to_ry_per_bohr(val_ev_ang: float) -> float:
    """Convert atomic force from eV/Å to Ry/Bohr."""
    return float(val_ev_ang) * EV_PER_ANGSTROM_TO_RY_PER_BOHR


def kbar_to_gpa(val_kbar: float) -> float:
    """Convert pressure/stress from kbar to GPa."""
    return float(val_kbar) * KBAR_TO_GPA


def gpa_to_kbar(val_gpa: float) -> float:
    """Convert pressure/stress from GPa to kbar."""
    return float(val_gpa) * GPA_TO_KBAR


def energy_ev_to_etot_conv_thr_ry(energy_tolerance_ev: float) -> float:
    """Convert internal ionic energy tolerance (eV) to QE etot_conv_thr (Ry) [SPEC-02]."""
    checked = _require_finite_positive(energy_tolerance_ev, "energy_tolerance_ev")
    return ev_to_ry(checked)


def force_ev_ang_to_forc_conv_thr_ry_bohr(force_tolerance_ev_per_angstrom: float) -> float:
    """Convert internal force tolerance (eV/Å) to QE forc_conv_thr (Ry/Bohr) [SPEC-02]."""
    checked = _require_finite_positive(
        force_tolerance_ev_per_angstrom, "force_tolerance_ev_per_angstrom"
    )
    return ev_per_angstrom_to_ry_per_bohr(checked)


def pressure_gpa_to_press_conv_thr_kbar(pressure_tolerance_gpa: float) -> float:
    """Convert internal cell pressure tolerance (GPa) to QE press_conv_thr (kbar) [SPEC-02]."""
    checked = _require_finite_positive(pressure_tolerance_gpa, "pressure_tolerance_gpa")
    return gpa_to_kbar(checked)
