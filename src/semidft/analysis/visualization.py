"""Matplotlib plotting utilities for semiconductor band structures and DOS."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from semidft.analysis.density_of_states import DOSData

matplotlib.use("Agg")


def plot_band_structure(
    distances: list[float],
    eigenvalues_ev: list[list[float]],
    vbm_ev: float,
    labels: list[str | None],
    output_path: Path,
    energy_window_ev: tuple[float, float] = (-6.0, 6.0),
) -> Path:
    """Plot electronic band structure shifted so E_VBM = 0 eV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(distances, dtype=float)
    eig_mat = np.asarray(eigenvalues_ev, dtype=float) - float(vbm_ev)

    fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=150)
    for b_idx in range(eig_mat.shape[1]):
        ax.plot(x, eig_mat[:, b_idx], color="#1f77b4", linewidth=1.2)

    ax.axhline(0.0, color="#d62728", linestyle="--", linewidth=0.9, label="VBM (0 eV)")
    tick_locs: list[float] = []
    tick_names: list[str] = []
    for dist, lbl in zip(distances, labels, strict=True):
        if lbl:
            tick_locs.append(dist)
            tick_names.append("Γ" if lbl == "GAMMA" else lbl)
            ax.axvline(dist, color="#888888", linestyle=":", linewidth=0.7)

    if tick_locs:
        ax.set_xticks(tick_locs)
        ax.set_xticklabels(tick_names)
    ax.set_xlim(float(x[0]), float(x[-1]))
    ax.set_ylim(energy_window_ev[0], energy_window_ev[1])
    ax.set_ylabel("Energy $E - E_{\\mathrm{VBM}}$ (eV)")
    ax.set_title("Electronic Band Structure (Kohn–Sham DFT)")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_dos(
    dos_data: DOSData,
    output_path: Path,
    energy_window_ev: tuple[float, float] = (-10.0, 10.0),
) -> Path:
    """Plot total electronic Density of States."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ref_e = dos_data.fermi_energy_ev or 0.0
    energies = np.asarray(dos_data.energies_ev, dtype=float) - ref_e
    dos = np.asarray(dos_data.dos_states_per_ev, dtype=float)

    fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=150)
    ax.plot(energies, dos, color="#2ca02c", linewidth=1.3)
    ax.axvline(0.0, color="#d62728", linestyle="--", linewidth=0.9)
    ax.set_xlim(energy_window_ev[0], energy_window_ev[1])
    ax.set_xlabel("Energy $E - E_F$ (eV)")
    ax.set_ylabel("DOS (states / eV / cell)")
    ax.set_title("Electronic Density of States")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
