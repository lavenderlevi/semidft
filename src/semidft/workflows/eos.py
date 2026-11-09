"""Birch-Murnaghan Equation of State (EOS) volume-sweep workflow [SPEC-06]."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from semidft.analysis.eos import BirchMurnaghanResult, fit_birch_murnaghan_eos
from semidft.core.exceptions import ConvergenceError
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    RunManifest,
    StructureRecord,
    TransformationStep,
)
from semidft.structures.validator import validate_structure


class EOSWorkflowResult(BaseModel):
    """Complete result of a Birch-Murnaghan EOS sweep across strained volumes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    strained_structures: list[StructureRecord]
    manifests: list[RunManifest]
    volumes_angstrom3: list[float]
    energies_ev: list[float]
    eos_fit: BirchMurnaghanResult


def compute_cell_volume_angstrom3(structure: StructureRecord) -> float:
    """Compute the unit-cell volume in Å^3 from the 3x3 lattice matrix."""
    mat = np.asarray(structure.lattice_matrix_angstrom, dtype=float)
    return float(abs(np.linalg.det(mat)))


def generate_eos_strained_structures(
    structure: StructureRecord,
    volume_scale_factors: list[float] | None = None,
) -> list[StructureRecord]:
    """Generate isotropically volume-scaled StructureRecords for Birch-Murnaghan EOS sweeps."""
    validated = validate_structure(structure)
    scales = volume_scale_factors or [0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06]
    base_lat = np.asarray(validated.lattice_matrix_angstrom, dtype=float)
    results: list[StructureRecord] = []

    for v_scale in scales:
        linear_scale = float(v_scale) ** (1.0 / 3.0)
        scaled_lat = (base_lat * linear_scale).tolist()
        step = TransformationStep(
            operation=f"eos_volume_scale_{v_scale:.4f}",
            transformation_matrix=[
                [linear_scale, 0.0, 0.0],
                [0.0, linear_scale, 0.0],
                [0.0, 0.0, linear_scale],
            ],
            determinant=float(v_scale),
            symprec_angstrom=validated.symprec_angstrom,
        )
        results.append(
            validated.model_copy(
                update={
                    "material_id": f"{validated.material_id}-v{v_scale:.3f}",
                    "lattice_matrix_angstrom": [[float(x) for x in row] for row in scaled_lat],
                    "transformation_history": [
                        *validated.transformation_history,
                        step,
                    ],
                }
            )
        )
    return results


class EOSWorkflow:
    """Orchestrate multi-volume SCF calculations and fit 3rd-order Birch-Murnaghan EOS."""

    def __init__(
        self,
        volume_scale_factors: list[float] | None = None,
        atoms_per_conventional_ratio: float = 4.0,
    ) -> None:
        self.volume_scale_factors = volume_scale_factors or [
            0.94,
            0.96,
            0.98,
            1.00,
            1.02,
            1.04,
            1.06,
        ]
        self.atoms_per_conventional_ratio = atoms_per_conventional_ratio

    def run(
        self,
        base_dir: Path,
        structure: StructureRecord,
        base_spec: CalculationSpec,
        runner_fn: Callable[[Path, StructureRecord, CalculationSpec], RunManifest],
    ) -> EOSWorkflowResult:
        """Execute fixed-volume calculations across strained volumes and fit Birch-Murnaghan EOS."""
        strained = generate_eos_strained_structures(structure, self.volume_scale_factors)
        manifests: list[RunManifest] = []
        volumes: list[float] = []
        energies: list[float] = []

        for scale, st in zip(self.volume_scale_factors, strained, strict=True):
            calc_id = f"{base_spec.calculation_id}-v{scale:.3f}".replace(".", "p")
            point_spec = base_spec.model_copy(
                update={
                    "calculation_id": calc_id,
                    "material_id": st.material_id,
                    "calculation_type": CalculationType.SCF,
                }
            )
            run_dir = base_dir / st.material_id / "runs" / calc_id
            run_dir.mkdir(parents=True, exist_ok=True)
            manifest = runner_fn(run_dir, st, point_spec)
            if not manifest.is_usable_for_downstream() or manifest.total_energy_ev is None:
                raise ConvergenceError(
                    f"EOS volume point {calc_id} failed to converge or is missing total_energy_ev."
                )
            manifests.append(manifest)
            volumes.append(compute_cell_volume_angstrom3(st))
            energies.append(manifest.total_energy_ev)

        fit = fit_birch_murnaghan_eos(
            volumes,
            energies,
            atoms_per_conventional_ratio=self.atoms_per_conventional_ratio,
        )
        return EOSWorkflowResult(
            strained_structures=strained,
            manifests=manifests,
            volumes_angstrom3=volumes,
            energies_ev=energies,
            eos_fit=fit,
        )
