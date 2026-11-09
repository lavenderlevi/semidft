"""Conduction Band Minimum (CBM) detector [SPEC-05]."""

from typing import Literal

from semidft.analysis.vbm_detector import BandEdge


def detect_cbm(
    eigenvalues_ev: list[list[float]],
    kpoints_fractional: list[tuple[float, float, float]],
    num_valence_bands: int,
    source: Literal["high_symmetry_path", "dense_kmesh", "local_refinement"] = "dense_kmesh",
    kpoint_labels: list[str | None] | None = None,
    spin_channel: Literal["unpolarized", "up", "down", "spinor"] = "unpolarized",
) -> BandEdge:
    """Locate the lowest unoccupied state across all k-points and conduction bands."""
    if not eigenvalues_ev or len(eigenvalues_ev) != len(kpoints_fractional):
        raise ValueError("eigenvalues_ev and kpoints_fractional must be non-empty and equal length")

    best_energy = float("inf")
    best_band = num_valence_bands + 1
    best_k: tuple[float, float, float] = kpoints_fractional[0]
    best_label: str | None = None

    for k_idx, band_eigs in enumerate(eigenvalues_ev):
        if len(band_eigs) <= num_valence_bands:
            raise ValueError(
                f"k-point {k_idx} has no conduction bands "
                f"(total={len(band_eigs)}, valence={num_valence_bands})"
            )
        for b_idx in range(num_valence_bands, len(band_eigs)):
            val = float(band_eigs[b_idx])
            if val < best_energy:
                best_energy = val
                best_band = b_idx + 1
                best_k = kpoints_fractional[k_idx]
                best_label = kpoint_labels[k_idx] if kpoint_labels else None

    return BandEdge(
        energy_ev=best_energy,
        band_index=best_band,
        kpoint_fractional=best_k,
        kpoint_label=best_label,
        spin_channel=spin_channel,
        occupation=0.0,
        source=source,
    )
