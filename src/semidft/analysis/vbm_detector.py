"""Valence Band Maximum (VBM) detector and unified BandEdge schema [SPEC-05]."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class BandEdge(BaseModel):
    """Electronic band extremum with k-point, band index, spin channel, and sampling source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    energy_ev: float
    band_index: int
    kpoint_fractional: tuple[float, float, float]
    kpoint_label: str | None = None
    spin_channel: Literal["unpolarized", "up", "down", "spinor"] = "unpolarized"
    occupation: float | None = 1.0
    source: Literal["high_symmetry_path", "dense_kmesh", "local_refinement"] = "dense_kmesh"


def detect_vbm(
    eigenvalues_ev: list[list[float]],
    kpoints_fractional: list[tuple[float, float, float]],
    num_valence_bands: int,
    source: Literal["high_symmetry_path", "dense_kmesh", "local_refinement"] = "dense_kmesh",
    kpoint_labels: list[str | None] | None = None,
    spin_channel: Literal["unpolarized", "up", "down", "spinor"] = "unpolarized",
) -> BandEdge:
    """Locate the highest occupied state across all k-points and valence bands."""
    if not eigenvalues_ev or len(eigenvalues_ev) != len(kpoints_fractional):
        raise ValueError("eigenvalues_ev and kpoints_fractional must be non-empty and equal length")
    if num_valence_bands <= 0:
        raise ValueError("num_valence_bands must be >= 1")

    best_energy = float("-inf")
    best_band = 0
    best_k: tuple[float, float, float] = kpoints_fractional[0]
    best_label: str | None = None

    for k_idx, band_eigs in enumerate(eigenvalues_ev):
        if len(band_eigs) < num_valence_bands:
            raise ValueError(
                f"k-point {k_idx} has only {len(band_eigs)} bands, need >= {num_valence_bands}"
            )
        for b_idx in range(num_valence_bands):
            val = float(band_eigs[b_idx])
            if val > best_energy:
                best_energy = val
                best_band = b_idx + 1  # 1-based band index
                best_k = kpoints_fractional[k_idx]
                best_label = kpoint_labels[k_idx] if kpoint_labels else None

    return BandEdge(
        energy_ev=best_energy,
        band_index=best_band,
        kpoint_fractional=best_k,
        kpoint_label=best_label,
        spin_channel=spin_channel,
        occupation=1.0,
        source=source,
    )
