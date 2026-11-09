"""3rd-order Birch-Murnaghan EOS fitting for equilibrium volume and bulk modulus [SPEC-06]."""

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict
from scipy.optimize import curve_fit

EV_PER_ANG3_TO_GPA: float = 160.2176634


class BirchMurnaghanResult(BaseModel):
    """Fitted Birch-Murnaghan EOS parameters and RMSE."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    equilibrium_energy_ev: float
    equilibrium_volume_angstrom3: float
    cubic_lattice_constant_a0_angstrom: float
    bulk_modulus_gpa: float
    b0_prime: float
    rmse_ev: float
    num_volume_points: int


def birch_murnaghan_energy_ev(
    volume_ang3: NDArray[np.float64],
    e0_ev: float,
    v0_ang3: float,
    b0_ev_ang3: float,
    b0_prime: float,
) -> NDArray[np.float64]:
    """Evaluate 3rd-order Birch-Murnaghan E(V) in eV."""
    eta = (v0_ang3 / volume_ang3) ** (2.0 / 3.0) - 1.0
    term1 = (eta**3) * b0_prime
    term2 = (eta**2) * (6.0 - 4.0 * ((v0_ang3 / volume_ang3) ** (2.0 / 3.0)))
    result: NDArray[np.float64] = e0_ev + (9.0 * v0_ang3 * b0_ev_ang3 / 16.0) * (term1 + term2)
    return result


def fit_birch_murnaghan_eos(
    volumes_angstrom3: list[float],
    energies_ev: list[float],
    atoms_per_conventional_ratio: float = 4.0,
) -> BirchMurnaghanResult:
    """Fit E(V) data to the 3rd-order Birch-Murnaghan EOS to obtain V0, a0, B0 (GPa), and B0'."""
    if len(volumes_angstrom3) < 5 or len(volumes_angstrom3) != len(energies_ev):
        raise ValueError("Birch-Murnaghan EOS fit requires at least 5 (V, E) points.")

    v_arr = np.asarray(volumes_angstrom3, dtype=np.float64)
    e_arr = np.asarray(energies_ev, dtype=np.float64)

    min_idx = int(np.argmin(e_arr))
    p0 = [float(e_arr[min_idx]), float(v_arr[min_idx]), 0.5, 4.0]
    popt, _ = curve_fit(birch_murnaghan_energy_ev, v_arr, e_arr, p0=p0, maxfev=10000)
    e0, v0, b0_ev_a3, b0_p = [float(x) for x in popt]

    fitted = birch_murnaghan_energy_ev(v_arr, e0, v0, b0_ev_a3, b0_p)
    rmse = float(np.sqrt(np.mean((e_arr - fitted) ** 2)))
    a0 = float((atoms_per_conventional_ratio * v0) ** (1.0 / 3.0))

    return BirchMurnaghanResult(
        equilibrium_energy_ev=e0,
        equilibrium_volume_angstrom3=v0,
        cubic_lattice_constant_a0_angstrom=a0,
        bulk_modulus_gpa=b0_ev_a3 * EV_PER_ANG3_TO_GPA,
        b0_prime=b0_p,
        rmse_ev=rmse,
        num_volume_points=len(volumes_angstrom3),
    )
