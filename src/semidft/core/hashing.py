"""Deterministic SHA-256 hashing for structures, inputs, and files."""

import hashlib
import json
from pathlib import Path
from typing import Any

from semidft.core.models import CalculationSpec, StructureRecord


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_structure_hash(structure: StructureRecord) -> str:
    """Compute a deterministic SHA-256 hash of crystallographic geometry and species."""
    rounded_lattice = [
        [round(float(val), 10) for val in row] for row in structure.lattice_matrix_angstrom
    ]
    rounded_coords = [
        [round(float(val) % 1.0, 10) for val in coord] for coord in structure.fractional_coords
    ]
    payload = {
        "species": list(structure.species),
        "lattice_matrix_angstrom": rounded_lattice,
        "fractional_coords": rounded_coords,
        "cell_type": structure.cell_type.value,
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def compute_input_hash(
    structure: StructureRecord,
    spec: CalculationSpec,
    pseudo_sha256: dict[str, str],
    qe_version: str,
    workflow_version: str = "1.0.0",
) -> str:
    """Compute SHA256(S + C + P + Q + W) for calculation provenance."""
    calc_payload = {
        "calculation_type": spec.calculation_type.value,
        "xc_functional": spec.xc_functional,
        "ecutwfc_ry": round(float(spec.ecutwfc_ry), 8),
        "ecutrho_ry": round(float(spec.ecutrho_ry), 8),
        "kpoints": list(spec.kpoints),
        "kpoint_offset": list(spec.kpoint_offset),
        "conv_thr_ry": float(spec.conv_thr_ry),
        "energy_tolerance_ev": round(float(spec.energy_tolerance_ev), 10),
        "force_tolerance_ev_per_angstrom": round(float(spec.force_tolerance_ev_per_angstrom), 10),
        "pressure_tolerance_gpa": round(float(spec.pressure_tolerance_gpa), 10),
        "occupations": spec.occupations,
        "smearing_type": spec.smearing_type,
        "degauss_ry": spec.degauss_ry,
        "nbnd": spec.nbnd,
        "spin_mode": spec.spin_mode,
    }
    combined = {
        "S_structure_hash": compute_structure_hash(structure),
        "C_calculation_parameters": calc_payload,
        "P_pseudo_sha256": {k: pseudo_sha256[k] for k in sorted(pseudo_sha256)},
        "Q_qe_version": str(qe_version).strip(),
        "W_workflow_version": str(workflow_version).strip(),
    }
    return hashlib.sha256(_canonical_json_bytes(combined)).hexdigest()


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 digest of a file on disk."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
