"""Parser for Quantum ESPRESSO pw.x text outputs converting units to internal conventions."""

import re

from pydantic import BaseModel, ConfigDict, Field

from semidft.core.units import (
    kbar_to_gpa,
    ry_per_bohr_to_ev_per_angstrom,
    ry_to_ev,
)


class ParsedPWOutput(BaseModel):
    """Structured data extracted from a pw.out file in internal units (eV, Å, GPa)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_done: bool = False
    scf_converged_flag: bool = False
    scf_not_converged_flag: bool = False
    bfgs_converged_flag: bool = False
    scf_iterations: int | None = None
    total_energy_ev: float | None = None
    final_energy_change_ev: float | None = None
    estimated_scf_accuracy_ry: float | None = None
    fermi_energy_ev: float | None = None
    highest_occupied_ev: float | None = None
    lowest_unoccupied_ev: float | None = None
    max_force_ev_per_angstrom: float | None = None
    total_force_ev_per_angstrom: float | None = None
    pressure_gpa: float | None = None
    max_stress_component_gpa: float | None = None
    stress_tensor_gpa: list[list[float]] | None = None
    relaxed_lattice_angstrom: list[list[float]] | None = None
    relaxed_species: list[str] | None = None
    relaxed_fractional_coords: list[list[float]] | None = None
    num_kpoints_computed: int = 0
    eigenvalues_ev: list[list[float]] = Field(default_factory=list)


def parse_pw_output(text: str) -> ParsedPWOutput:
    """Parse a pw.x standard output string into a ParsedPWOutput record."""
    job_done = "JOB DONE." in text
    scf_not_conv = "convergence NOT achieved" in text

    scf_matches = list(re.finditer(r"convergence has been achieved in\s+(\d+)\s+iterations", text))
    scf_conv = len(scf_matches) > 0 and not scf_not_conv
    scf_iters = int(scf_matches[-1].group(1)) if scf_matches else None

    bfgs_conv = "End of BFGS Geometry Optimization" in text or "bfgs converged" in text

    energy_matches = list(re.finditer(r"!\s+total energy\s+=\s+([-+]?\d+\.\d+)\s+Ry", text))
    energies_ev = [ry_to_ev(float(m.group(1))) for m in energy_matches]
    total_energy_ev = energies_ev[-1] if energies_ev else None
    final_de_ev = (
        abs(energies_ev[-1] - energies_ev[-2])
        if len(energies_ev) >= 2
        else (0.0 if energies_ev else None)
    )

    acc_matches = list(
        re.finditer(
            r"estimated scf accuracy\s+<\s+([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s+Ry", text
        )
    )
    est_acc_ry = float(acc_matches[-1].group(1)) if acc_matches else None

    fermi_match = re.search(r"the Fermi energy is\s+([-+]?\d+\.\d+)\s+ev", text)
    fermi_ev = float(fermi_match.group(1)) if fermi_match else None

    hl_match = re.search(
        r"highest occupied, lowest unoccupied level \(ev\):\s+([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)",
        text,
    )
    vbm_ev = float(hl_match.group(1)) if hl_match else None
    cbm_ev = float(hl_match.group(2)) if hl_match else None

    tot_force_matches = list(re.finditer(r"Total force\s*=\s*([-+]?\d+\.\d+)", text))
    tot_force_ev_ang = (
        ry_per_bohr_to_ev_per_angstrom(float(tot_force_matches[-1].group(1)))
        if tot_force_matches
        else None
    )

    atom_force_matches = list(
        re.finditer(
            r"atom\s+\d+\s+type\s+\d+\s+force\s*=\s*"
            r"([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)",
            text,
        )
    )
    max_force_ev_ang: float | None = tot_force_ev_ang
    if atom_force_matches:
        norms = [
            (float(m.group(1)) ** 2 + float(m.group(2)) ** 2 + float(m.group(3)) ** 2) ** 0.5
            for m in atom_force_matches
        ]
        max_force_ev_ang = ry_per_bohr_to_ev_per_angstrom(max(norms))

    stress_block = re.search(
        r"total\s+stress\s+\(Ry/bohr\*\*3\)\s+\(kbar\)\s+P=\s*([-+]?\d+\.\d+)\s*\n"
        r"([^\n]+\n[^\n]+\n[^\n]+)",
        text,
    )
    pressure_gpa: float | None = None
    stress_tensor_gpa: list[list[float]] | None = None
    max_stress_gpa: float | None = None
    if stress_block:
        pressure_gpa = kbar_to_gpa(float(stress_block.group(1)))
        rows_gpa: list[list[float]] = []
        for line in stress_block.group(2).strip().splitlines():
            parts = [float(x) for x in line.split()]
            if len(parts) == 6:
                kbar_row = [kbar_to_gpa(v) for v in parts[3:6]]
                rows_gpa.append(kbar_row)
        if len(rows_gpa) == 3:
            stress_tensor_gpa = rows_gpa
            max_stress_gpa = max(abs(val) for row in rows_gpa for val in row)

    k_blocks = re.findall(
        r"k\s*=\s*[-+]?\d+\.\d+\s*[-+]?\d+\.\d+\s*[-+]?\d+\.\d+[^\n]*?"
        r"(?:bands|band energies)\s*\(ev\):\s*\n\s*\n((?:\s*[-+]?\d+\.\d+[^\n]*\n)+)",
        text,
        flags=re.IGNORECASE,
    )
    eigenvalues_ev: list[list[float]] = []
    for block in k_blocks:
        vals = [float(v) for v in re.findall(r"[-+]?\d+\.\d+", block)]
        if vals:
            eigenvalues_ev.append(vals)

    return ParsedPWOutput(
        job_done=job_done,
        scf_converged_flag=scf_conv,
        scf_not_converged_flag=scf_not_conv,
        bfgs_converged_flag=bfgs_conv,
        scf_iterations=scf_iters,
        total_energy_ev=total_energy_ev,
        final_energy_change_ev=final_de_ev,
        estimated_scf_accuracy_ry=est_acc_ry,
        fermi_energy_ev=fermi_ev,
        highest_occupied_ev=vbm_ev,
        lowest_unoccupied_ev=cbm_ev,
        max_force_ev_per_angstrom=max_force_ev_ang,
        total_force_ev_per_angstrom=tot_force_ev_ang,
        pressure_gpa=pressure_gpa,
        max_stress_component_gpa=max_stress_gpa,
        stress_tensor_gpa=stress_tensor_gpa,
        num_kpoints_computed=len(eigenvalues_ev),
        eigenvalues_ev=eigenvalues_ev,
    )
