"""High-symmetry Brillouin-zone k-path generation enforcing seekpath cell consistency [SPEC-04]."""

import numpy as np
import seekpath
from pydantic import BaseModel, ConfigDict

from semidft.core.models import CellType, StructureRecord, TransformationStep
from semidft.structures.symmetry import structure_to_spglib_cell


class HighSymmetryKPath(BaseModel):
    """Explicit k-point path in crystal (reciprocal fractional) coordinates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    high_symmetry_points: dict[str, tuple[float, float, float]]
    path_segments: list[tuple[str, str]]
    kpoints_fractional: list[tuple[float, float, float]]
    kpoints_linear_distance: list[float]
    kpoint_labels: list[str | None]

    def to_crystal_b_points(
        self, points_per_segment: int = 30
    ) -> list[tuple[float, float, float, int]]:
        """Format path segments as Quantum ESPRESSO K_POINTS crystal_b entries."""
        entries: list[tuple[float, float, float, int]] = []
        for idx, (start_label, end_label) in enumerate(self.path_segments):
            s_pt = self.high_symmetry_points[start_label]
            entries.append((s_pt[0], s_pt[1], s_pt[2], points_per_segment))
            is_last_or_discontinuous = (
                idx + 1 == len(self.path_segments) or self.path_segments[idx + 1][0] != end_label
            )
            if is_last_or_discontinuous:
                e_pt = self.high_symmetry_points[end_label]
                entries.append((e_pt[0], e_pt[1], e_pt[2], 1))
        return entries


def generate_high_symmetry_kpath(
    record: StructureRecord,
    points_per_segment: int = 30,
    symprec_angstrom: float = 1e-3,
) -> tuple[StructureRecord, HighSymmetryKPath]:
    """Return seekpath standardized primitive StructureRecord and matched k-path [SPEC-04]."""
    lattice, positions, numbers, int_to_symbol = structure_to_spglib_cell(record)
    reference_distance = 1.0 / max(5, points_per_segment)

    res = seekpath.get_explicit_k_path(
        (lattice, positions, numbers),
        with_time_reversal=True,
        reference_distance=reference_distance,
        symprec=symprec_angstrom,
    )

    prim_lattice = [[float(v) for v in row] for row in res["primitive_lattice"].tolist()]
    prim_positions = [[float(v) % 1.0 for v in row] for row in res["primitive_positions"].tolist()]
    prim_types = [int_to_symbol[int(t)] for t in res["primitive_types"]]
    raw_trans_mat = res.get(
        "primitive_transformation_matrix",
        res.get("transformation_matrix", np.eye(3)),
    )
    trans_mat = [[float(v) for v in row] for row in np.asarray(raw_trans_mat).tolist()]

    step = TransformationStep(
        operation="seekpath_standardize_primitive",
        transformation_matrix=trans_mat,
        determinant=float(abs(np.linalg.det(np.asarray(trans_mat, dtype=float)))),
        symprec_angstrom=symprec_angstrom,
    )
    standardized_record = StructureRecord(
        material_id=record.material_id,
        formula=record.formula,
        lattice_matrix_angstrom=prim_lattice,
        species=prim_types,
        fractional_coords=prim_positions,
        space_group_symbol=(
            str(res.get("spacegroup_international", "")).strip() or record.space_group_symbol
        ),
        space_group_number=(int(res.get("spacegroup_number", 0)) or record.space_group_number),
        symprec_angstrom=symprec_angstrom,
        cell_type=CellType.PRIMITIVE,
        source_file=record.source_file,
        source_format=record.source_format,
        transformation_history=[*record.transformation_history, step],
    )

    hs_points = {
        str(k): (float(v[0]), float(v[1]), float(v[2])) for k, v in res["point_coords"].items()
    }
    segments = [(str(a), str(b)) for a, b in res["path"]]
    rel_kpts = [
        (float(row[0]), float(row[1]), float(row[2]))
        for row in res["explicit_kpoints_rel"].tolist()
    ]
    linear_dist = [float(x) for x in res["explicit_kpoints_linearcoord"].tolist()]
    labels = [str(lbl) if lbl else None for lbl in res["explicit_kpoints_labels"]]

    return (
        standardized_record,
        HighSymmetryKPath(
            high_symmetry_points=hs_points,
            path_segments=segments,
            kpoints_fractional=rel_kpts,
            kpoints_linear_distance=linear_dist,
            kpoint_labels=labels,
        ),
    )
