"""Unit tests for scientific benchmark validation and report generation [SPEC-05, SPEC-06]."""

import json
from pathlib import Path

from semidft.analysis.gap_classifier import classify_electronic_gap
from semidft.analysis.report import generate_json_report, generate_markdown_report
from semidft.analysis.validation import (
    load_benchmark_references,
    validate_against_benchmark,
)
from semidft.core.models import (
    CalculationType,
    ExecutionStatus,
    RunManifest,
    ValidationStatus,
)


def test_validate_silicon_against_pbe_and_experimental_benchmarks_spec_05_06() -> None:
    benchmarks = load_benchmark_references(Path("configs/benchmarks/reference_semiconductors.yaml"))
    si_bench = benchmarks["Si"]

    kpts = [(0.0, 0.0, 0.0), (0.42, 0.0, 0.42)]
    eigs = [
        [-6.0, 3.0, 6.00, 6.00, 8.55],
        [-5.0, 2.0, 4.10, 4.20, 6.57],
    ]
    gap_rep = classify_electronic_gap(
        eigs,
        kpts,
        num_valence_bands=4,
        xc_functional="PBE",
        experimental_ref=si_bench.experimental_gap,
    )

    val = validate_against_benchmark(
        material_symbol="Si",
        computed_a0_angstrom=5.468,
        computed_b0_gpa=88.6,
        gap_report=gap_rep,
        benchmark=si_bench,
    )
    assert val.pbe_lattice_agreed is True
    assert val.pbe_bulk_modulus_agreed is True
    assert val.pbe_gap_agreed is True
    assert val.gap_topology_agreed is True
    assert val.experimental_gap_deviation_ev is not None

    manifest = RunManifest(
        calculation_id="si-scf-001",
        material_id="silicon-diamond",
        calculation_type=CalculationType.SCF,
        execution_status=ExecutionStatus.COMPLETED,
        validation_status=ValidationStatus.CONVERGED,
        exit_code=0,
        structure_hash="s" * 64,
        input_hash="i" * 64,
        qe_version="7.5",
        xc_functional="PBE",
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        pseudo_checksums={"Si": "p" * 64},
        total_energy_ev=-215.56,
    )
    md = generate_markdown_report(manifest, gap_rep, val)
    assert "Kohn–Sham PBE Fundamental Gap" in md
    assert "10.1063/1.1368156" in md
    assert "COMPLETED" in md and "CONVERGED" in md

    json_str = generate_json_report(manifest, gap_rep, val)
    payload = json.loads(json_str)
    assert payload["schema_version"] == "1.0.0"
    assert payload["manifest"]["calculation_id"] == "si-scf-001"
    assert payload["validation"]["pbe_gap_agreed"] is True
