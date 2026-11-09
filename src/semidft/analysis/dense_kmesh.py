"""Dense uniform NSCF k-point mesh eigenvalue analysis [SPEC-05]."""

from pydantic import BaseModel, ConfigDict

from semidft.analysis.cbm_detector import detect_cbm
from semidft.analysis.vbm_detector import BandEdge, detect_vbm


class DenseKMeshSummary(BaseModel):
    """Mesh-resolved band extrema and valley degeneracy diagnostics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mesh_shape: list[int]
    num_kpoints: int
    vbm: BandEdge
    cbm: BandEdge
    mesh_resolved_gap_ev: float
    recommends_local_refinement: bool


DenseKMeshEigenvalues = DenseKMeshSummary


def analyze_dense_kmesh(
    eigenvalues_ev: list[list[float]],
    kpoints_fractional: list[tuple[float, float, float]],
    num_valence_bands: int,
    mesh_shape: list[int],
) -> DenseKMeshSummary:
    """Extract mesh-resolved VBM and CBM and check whether local refinement is needed."""
    vbm = detect_vbm(eigenvalues_ev, kpoints_fractional, num_valence_bands, source="dense_kmesh")
    cbm = detect_cbm(eigenvalues_ev, kpoints_fractional, num_valence_bands, source="dense_kmesh")
    gap = max(0.0, cbm.energy_ev - vbm.energy_ev)

    cb_mins = sorted(min(row[num_valence_bands:]) for row in eigenvalues_ev)
    near_degenerate = len(cb_mins) >= 2 and (cb_mins[1] - cb_mins[0]) < 0.015

    return DenseKMeshSummary(
        mesh_shape=mesh_shape,
        num_kpoints=len(kpoints_fractional),
        vbm=vbm,
        cbm=cbm,
        mesh_resolved_gap_ev=gap,
        recommends_local_refinement=near_degenerate,
    )
