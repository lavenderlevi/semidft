"""Method-consistent PBE benchmark validation vs experimental context [SPEC-05, SPEC-06]."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from semidft.analysis.gap_classifier import (
    ElectronicGapReport,
    ExperimentalGapReference,
)


class PBEProtocolMetadata(BaseModel):
    """Protocol metadata for a PBE reference calculation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    xc_functional: str
    pseudopotential_set: str
    ecutwfc_ry: float
    ecutrho_ry: float
    kpoints: list[int]
    reference_doi: str


class MaterialBenchmarkReference(BaseModel):
    """Curated PBE and experimental benchmark reference for a semiconductor."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    space_group_number: int
    pbe_protocol: PBEProtocolMetadata
    pbe_lattice_a0_angstrom: float
    pbe_lattice_tolerance_angstrom: float
    pbe_bulk_modulus_gpa: float
    pbe_bulk_modulus_tolerance_gpa: float
    pbe_fundamental_gap_ev: float
    pbe_gap_tolerance_ev: float
    expected_gap_type: Literal["direct", "indirect"]
    expected_vbm_kpoint: tuple[float, float, float]
    experimental_lattice_300k_angstrom: float
    experimental_bulk_modulus_gpa: float
    experimental_gap: ExperimentalGapReference


class ScientificValidationSummary(BaseModel):
    """Comparison of computed DFT properties against PBE references and experiments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_symbol: str
    pbe_lattice_agreed: bool | None = None
    pbe_lattice_diff_angstrom: float | None = None
    pbe_bulk_modulus_agreed: bool | None = None
    pbe_bulk_modulus_diff_gpa: float | None = None
    pbe_gap_agreed: bool | None = None
    pbe_gap_diff_ev: float | None = None
    gap_topology_agreed: bool | None = None
    experimental_lattice_deviation_angstrom: float | None = None
    experimental_gap_deviation_ev: float | None = None


def load_benchmark_references(
    path: Path = Path("configs/benchmarks/reference_semiconductors.yaml"),
) -> dict[str, MaterialBenchmarkReference]:
    """Load material benchmark references from YAML."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    materials = raw.get("materials", {})
    return {str(k): MaterialBenchmarkReference.model_validate(v) for k, v in materials.items()}


def validate_against_benchmark(
    material_symbol: str,
    computed_a0_angstrom: float | None,
    computed_b0_gpa: float | None,
    gap_report: ElectronicGapReport | None,
    benchmark: MaterialBenchmarkReference,
) -> ScientificValidationSummary:
    """Compare computed values against PBE tolerances and compute experimental deviations."""
    lat_ok: bool | None = None
    lat_diff_pbe: float | None = None
    lat_diff_exp: float | None = None
    if computed_a0_angstrom is not None:
        lat_diff_pbe = computed_a0_angstrom - benchmark.pbe_lattice_a0_angstrom
        lat_ok = abs(lat_diff_pbe) <= benchmark.pbe_lattice_tolerance_angstrom
        lat_diff_exp = computed_a0_angstrom - benchmark.experimental_lattice_300k_angstrom

    b0_ok: bool | None = None
    b0_diff_pbe: float | None = None
    if computed_b0_gpa is not None:
        b0_diff_pbe = computed_b0_gpa - benchmark.pbe_bulk_modulus_gpa
        b0_ok = abs(b0_diff_pbe) <= benchmark.pbe_bulk_modulus_tolerance_gpa

    gap_ok: bool | None = None
    gap_diff_pbe: float | None = None
    topo_ok: bool | None = None
    gap_diff_exp: float | None = None
    if gap_report is not None:
        val_ev = gap_report.fundamental_gap.value_ev
        gap_diff_pbe = val_ev - benchmark.pbe_fundamental_gap_ev
        gap_ok = abs(gap_diff_pbe) <= benchmark.pbe_gap_tolerance_ev
        topo_ok = gap_report.gap_classification == benchmark.expected_gap_type
        gap_diff_exp = val_ev - benchmark.experimental_gap.value_ev

    return ScientificValidationSummary(
        material_symbol=material_symbol,
        pbe_lattice_agreed=lat_ok,
        pbe_lattice_diff_angstrom=lat_diff_pbe,
        pbe_bulk_modulus_agreed=b0_ok,
        pbe_bulk_modulus_diff_gpa=b0_diff_pbe,
        pbe_gap_agreed=gap_ok,
        pbe_gap_diff_ev=gap_diff_pbe,
        gap_topology_agreed=topo_ok,
        experimental_lattice_deviation_angstrom=lat_diff_exp,
        experimental_gap_deviation_ev=gap_diff_exp,
    )
