"""Fundamental and direct band-gap classifier modulo reciprocal lattice translations [SPEC-05]."""

from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from semidft.analysis.cbm_detector import detect_cbm
from semidft.analysis.vbm_detector import BandEdge, detect_vbm
from semidft.core.schemas import CURRENT_SCHEMA_VERSION


class ExperimentalGapSource(BaseModel):
    """Literature citation metadata for experimental reference band gaps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    doi: str | None = None
    citation: str | None = None
    url: str | None = None


class ExperimentalGapReference(BaseModel):
    """Structured experimental band-gap metadata with temperature and phase [SPEC-05]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value_ev: float
    temperature_k: float
    phase: str
    gap_definition: Literal["fundamental_electronic", "optical_absorption"] = (
        "fundamental_electronic"
    )
    uncertainty_ev: float | None = None
    source: ExperimentalGapSource


class FundamentalGapInfo(BaseModel):
    """Global fundamental band gap and its VBM/CBM band edges."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value_ev: float
    vbm: BandEdge
    cbm: BandEdge


class DirectGapInfo(BaseModel):
    """Minimum vertical (same k-point) transition energy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value_ev: float
    kpoint_fractional: tuple[float, float, float]


class GapSamplingMetadata(BaseModel):
    """Provenance of k-space sampling used to determine band extrema [SPEC-05]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path_based: bool
    dense_mesh_based: bool
    dense_kmesh: list[int] | None = None
    local_refinement: bool = False
    resolution_note: str = (
        "Mesh-resolved and high-symmetry path extrema without Wannier interpolation."
    )


class ElectronicGapReport(BaseModel):
    """Complete electronic gap classification report [SPEC-05]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = CURRENT_SCHEMA_VERSION
    xc_functional: str
    gap_classification: Literal["direct", "indirect", "metallic"]
    fundamental_gap: FundamentalGapInfo
    minimum_direct_gap: DirectGapInfo
    sampling: GapSamplingMetadata
    experimental_reference_gap: ExperimentalGapReference | None = None
    systematic_error_note: str = (
        "Semilocal PBE systematically underestimates semiconductor fundamental band gaps "
        "due to the missing exchange-correlation derivative discontinuity."
    )


def are_kpoints_equivalent_mod_lattice(
    k1: tuple[float, float, float],
    k2: tuple[float, float, float],
    tolerance: float = 1e-3,
) -> bool:
    """Return True if two fractional k-points are equivalent modulo reciprocal lattice Z^3."""
    diff = np.asarray(k1, dtype=float) - np.asarray(k2, dtype=float)
    wrapped = diff - np.round(diff)
    return bool(float(np.linalg.norm(wrapped)) <= tolerance)


def classify_electronic_gap(
    eigenvalues_ev: list[list[float]],
    kpoints_fractional: list[tuple[float, float, float]],
    num_valence_bands: int,
    xc_functional: str = "PBE",
    source: Literal["high_symmetry_path", "dense_kmesh", "local_refinement"] = "dense_kmesh",
    dense_kmesh_shape: list[int] | None = None,
    experimental_ref: ExperimentalGapReference | None = None,
    kpoint_tolerance_fractional: float = 1e-3,
) -> ElectronicGapReport:
    """Compute fundamental gap, minimum direct gap, and direct/indirect classification [SPEC-05]."""
    vbm = detect_vbm(eigenvalues_ev, kpoints_fractional, num_valence_bands, source=source)
    cbm = detect_cbm(eigenvalues_ev, kpoints_fractional, num_valence_bands, source=source)
    fundamental_val = cbm.energy_ev - vbm.energy_ev

    min_direct = float("inf")
    min_direct_k = kpoints_fractional[0]
    for k_idx, row in enumerate(eigenvalues_ev):
        vb_max_k = max(float(v) for v in row[:num_valence_bands])
        cb_min_k = min(float(v) for v in row[num_valence_bands:])
        direct_k = cb_min_k - vb_max_k
        if direct_k < min_direct:
            min_direct = direct_k
            min_direct_k = kpoints_fractional[k_idx]

    if fundamental_val <= 1e-4:
        gap_type: Literal["direct", "indirect", "metallic"] = "metallic"
    elif are_kpoints_equivalent_mod_lattice(
        vbm.kpoint_fractional,
        cbm.kpoint_fractional,
        tolerance=kpoint_tolerance_fractional,
    ):
        gap_type = "direct"
    else:
        gap_type = "indirect"

    return ElectronicGapReport(
        xc_functional=xc_functional,
        gap_classification=gap_type,
        fundamental_gap=FundamentalGapInfo(
            value_ev=max(0.0, fundamental_val),
            vbm=vbm,
            cbm=cbm,
        ),
        minimum_direct_gap=DirectGapInfo(
            value_ev=max(0.0, min_direct),
            kpoint_fractional=min_direct_k,
        ),
        sampling=GapSamplingMetadata(
            path_based=(source == "high_symmetry_path"),
            dense_mesh_based=(source == "dense_kmesh" or dense_kmesh_shape is not None),
            dense_kmesh=dense_kmesh_shape,
            local_refinement=(source == "local_refinement"),
        ),
        experimental_reference_gap=experimental_ref,
    )
