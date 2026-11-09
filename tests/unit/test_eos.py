import math

import numpy as np

from semidft.analysis.eos import (
    EV_PER_ANG3_TO_GPA,
    birch_murnaghan_energy_ev,
    fit_birch_murnaghan_eos,
)
from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure
from semidft.workflows.eos import generate_eos_strained_structures


def test_birch_murnaghan_eos_recovers_silicon_bulk_modulus_spec_06() -> None:
    # Silicon primitive cell V0 = 40.88 Å^3 (a0 = 5.468 Å), B0 = 88.5 GPa, B0' = 4.25
    true_e0 = -215.560
    true_v0 = 40.88
    true_b0_gpa = 88.5
    true_b0_ev_ang3 = true_b0_gpa / EV_PER_ANG3_TO_GPA
    true_b0_prime = 4.25

    scales = [0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06]
    vols = [true_v0 * s for s in scales]
    energies = birch_murnaghan_energy_ev(
        np.asarray(vols), true_e0, true_v0, true_b0_ev_ang3, true_b0_prime
    ).tolist()

    res = fit_birch_murnaghan_eos(vols, energies, atoms_per_conventional_ratio=4.0)
    assert math.isclose(res.equilibrium_volume_angstrom3, true_v0, rel_tol=1e-5)
    assert math.isclose(res.bulk_modulus_gpa, true_b0_gpa, rel_tol=1e-4)
    assert math.isclose(res.b0_prime, true_b0_prime, rel_tol=1e-3)
    assert math.isclose(
        res.cubic_lattice_constant_a0_angstrom,
        (4.0 * true_v0) ** (1.0 / 3.0),
        rel_tol=1e-5,
    )


def test_generate_eos_strained_structures_scales_volumes() -> None:
    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    strained = generate_eos_strained_structures(si, [0.95, 1.00, 1.05])
    assert len(strained) == 3
    v0 = float(abs(np.linalg.det(np.asarray(si.lattice_matrix_angstrom, dtype=float))))
    v_095 = float(abs(np.linalg.det(np.asarray(strained[0].lattice_matrix_angstrom, dtype=float))))
    assert math.isclose(v_095, 0.95 * v0, rel_tol=1e-9)
