"""Deterministic Quantum ESPRESSO input generator for pw.x, bands.x, and dos.x."""

from pathlib import Path

from semidft.core.exceptions import QEConfigurationError
from semidft.core.models import CalculationSpec, CalculationType, StructureRecord
from semidft.core.units import (
    energy_ev_to_etot_conv_thr_ry,
    force_ev_ang_to_forc_conv_thr_ry_bohr,
    pressure_gpa_to_press_conv_thr_kbar,
)

ATOMIC_MASSES_AMU: dict[str, float] = {
    "B": 10.81,
    "C": 12.011,
    "N": 14.007,
    "Al": 26.9815,
    "Si": 28.085,
    "P": 30.9738,
    "Ga": 69.723,
    "Ge": 72.63,
    "As": 74.9216,
    "In": 114.818,
    "Sb": 121.76,
}


def generate_pw_input(
    structure: StructureRecord,
    spec: CalculationSpec,
    pseudo_dir: Path = Path("./pseudo"),
    outdir: Path = Path("./scratch"),
    prefix: str = "semidft",
    kpath_crystal_b: list[tuple[float, float, float, int]] | None = None,
    dry_run: bool = False,
) -> str:
    """Render a deterministic pw.x input file converting internal tolerances to QE units."""
    unique_species = sorted(set(structure.species))
    for sp in unique_species:
        if sp not in spec.pseudopotentials:
            raise QEConfigurationError(f"Missing pseudopotential filename for species {sp!r}")

    etot_ry = energy_ev_to_etot_conv_thr_ry(spec.energy_tolerance_ev)
    forc_ry_bohr = force_ev_ang_to_forc_conv_thr_ry_bohr(spec.force_tolerance_ev_per_angstrom)
    press_kbar = pressure_gpa_to_press_conv_thr_kbar(spec.pressure_tolerance_gpa)

    is_relax = spec.calculation_type in (CalculationType.RELAX, CalculationType.VC_RELAX)
    nstep_val = 0 if dry_run else spec.nstep

    lines: list[str] = [
        "&CONTROL",
        f"  calculation = '{spec.calculation_type.value}'",
        f"  prefix = '{prefix}'",
        f"  outdir = '{outdir.as_posix()}'",
        f"  pseudo_dir = '{pseudo_dir.as_posix()}'",
        "  verbosity = 'high'",
        "  tprnfor = .true.",
        "  tstress = .true.",
        f"  disk_io = '{spec.disk_io}'",
        f"  etot_conv_thr = {etot_ry:.8e}",
        f"  forc_conv_thr = {forc_ry_bohr:.8e}",
    ]
    if is_relax or dry_run:
        lines.append(f"  nstep = {nstep_val}")
    lines.append("/")

    nbnd_val = spec.nbnd
    if nbnd_val is None and spec.calculation_type in (
        CalculationType.SCF,
        CalculationType.BANDS,
        CalculationType.NSCF,
    ):
        nbnd_val = max(8, len(structure.species) * 4)

    lines.extend(
        [
            "&SYSTEM",
            "  ibrav = 0",
            f"  nat = {len(structure.species)}",
            f"  ntyp = {len(unique_species)}",
            f"  ecutwfc = {spec.ecutwfc_ry:.6f}",
            f"  ecutrho = {spec.ecutrho_ry:.6f}",
            f"  input_dft = '{spec.xc_functional}'",
            f"  occupations = '{spec.occupations}'",
        ]
    )
    if spec.occupations == "smearing" and spec.smearing_type and spec.degauss_ry:
        lines.append(f"  smearing = '{spec.smearing_type}'")
        lines.append(f"  degauss = {spec.degauss_ry:.6f}")
    if nbnd_val is not None:
        lines.append(f"  nbnd = {nbnd_val}")
    if spec.spin_mode == "collinear":
        lines.append("  nspin = 2")
    elif spec.spin_mode == "noncollinear_soc":
        lines.append("  noncolin = .true.")
        lines.append("  lspinorb = .true.")
    lines.append("/")

    lines.extend(
        [
            "&ELECTRONS",
            f"  conv_thr = {spec.conv_thr_ry:.8e}",
            f"  electron_maxstep = {spec.electron_maxstep}",
            "  mixing_beta = 0.7",
            "/",
        ]
    )

    if is_relax:
        lines.extend(["&IONS", "  ion_dynamics = 'bfgs'", "/"])
    if spec.calculation_type == CalculationType.VC_RELAX:
        lines.extend(
            [
                "&CELL",
                "  cell_dynamics = 'bfgs'",
                f"  press_conv_thr = {press_kbar:.6f}",
                "/",
            ]
        )

    lines.append("ATOMIC_SPECIES")
    for sp in unique_species:
        mass = ATOMIC_MASSES_AMU.get(sp, 28.0)
        lines.append(f"  {sp}  {mass:.4f}  {spec.pseudopotentials[sp]}")

    lines.append("CELL_PARAMETERS angstrom")
    for row in structure.lattice_matrix_angstrom:
        lines.append(f"  {row[0]:16.10f}  {row[1]:16.10f}  {row[2]:16.10f}")

    lines.append("ATOMIC_POSITIONS crystal")
    for sp, coord in zip(structure.species, structure.fractional_coords, strict=True):
        lines.append(f"  {sp:<3s}  {coord[0]:16.10f}  {coord[1]:16.10f}  {coord[2]:16.10f}")

    if spec.calculation_type == CalculationType.BANDS and kpath_crystal_b is not None:
        lines.append("K_POINTS crystal_b")
        lines.append(f"  {len(kpath_crystal_b)}")
        for kx, ky, kz, weight in kpath_crystal_b:
            lines.append(f"  {kx:14.10f}  {ky:14.10f}  {kz:14.10f}  {weight}")
    else:
        k1, k2, k3 = spec.kpoints
        s1, s2, s3 = spec.kpoint_offset
        lines.append("K_POINTS automatic")
        lines.append(f"  {k1} {k2} {k3} {s1} {s2} {s3}")

    return "\n".join(lines) + "\n"


def generate_bands_x_input(
    prefix: str = "semidft",
    outdir: Path = Path("./scratch"),
    filband: str = "bands.dat",
) -> str:
    """Render a bands.x post-processing input file."""
    return (
        "&BANDS\n"
        f"  prefix = '{prefix}'\n"
        f"  outdir = '{outdir.as_posix()}'\n"
        f"  filband = '{filband}'\n"
        "  lsym = .true.\n"
        "/\n"
    )


def generate_dos_x_input(
    prefix: str = "semidft",
    outdir: Path = Path("./scratch"),
    fildos: str = "pwscf.dos",
    emin_ev: float = -20.0,
    emax_ev: float = 20.0,
    delta_e_ev: float = 0.02,
) -> str:
    """Render a dos.x post-processing input file."""
    return (
        "&DOS\n"
        f"  prefix = '{prefix}'\n"
        f"  outdir = '{outdir.as_posix()}'\n"
        f"  fildos = '{fildos}'\n"
        f"  Emin = {emin_ev:.4f}\n"
        f"  Emax = {emax_ev:.4f}\n"
        f"  DeltaE = {delta_e_ev:.4f}\n"
        "/\n"
    )
