"""Tier 5 versioned regression suite for QE 7.5 parser, band-gap report, and manifest [SPEC-07]."""

import json
import math
from pathlib import Path

from semidft.analysis.gap_classifier import classify_electronic_gap
from semidft.core.models import RunManifest
from semidft.core.schemas import validate_schema_version
from semidft.engines.qe.output_parser import parse_pw_output


def test_qe_7_5_silicon_scf_parser_regression_spec_07() -> None:
    raw_out = Path("tests/regression/fixtures/qe_7_5/silicon_scf.out").read_text(encoding="utf-8")
    expected = json.loads(
        Path("tests/regression/expected/silicon_scf.json").read_text(encoding="utf-8")
    )
    validate_schema_version(expected)

    parsed = parse_pw_output(raw_out)
    assert parsed.job_done is expected["job_done"]
    assert parsed.scf_converged_flag is expected["scf_converged_flag"]
    assert parsed.scf_iterations == expected["scf_iterations"]
    assert math.isclose(parsed.total_energy_ev or 0.0, expected["total_energy_ev"], rel_tol=1e-9)
    assert math.isclose(parsed.fermi_energy_ev or 0.0, expected["fermi_energy_ev"], rel_tol=1e-9)


def test_qe_7_5_silicon_band_gap_and_manifest_schema_regression_spec_07() -> None:
    expected_gap = json.loads(
        Path("tests/regression/expected/silicon_band_gap.json").read_text(encoding="utf-8")
    )
    validate_schema_version(expected_gap)

    kpts = [(0.0, 0.0, 0.0), (0.42, 0.0, 0.42), (0.5, 0.5, 0.5)]
    eigs = [
        [-5.9820, 3.0120, 6.0120, 6.0120, 8.5620, 8.5620, 8.5620, 9.2100],
        [-5.0120, 2.0450, 4.1200, 4.2100, 6.5920, 8.1200, 8.3400, 9.4500],
        [-4.5100, 2.5100, 4.8120, 4.8120, 7.4200, 8.9100, 8.9100, 10.1200],
    ]
    report = classify_electronic_gap(
        eigenvalues_ev=eigs,
        kpoints_fractional=kpts,
        num_valence_bands=4,
        xc_functional="PBE",
        source="high_symmetry_path",
    )
    assert report.gap_classification == expected_gap["gap_classification"]
    assert math.isclose(
        report.fundamental_gap.value_ev,
        expected_gap["fundamental_gap"]["value_ev"],
        rel_tol=1e-9,
    )
    assert math.isclose(
        report.minimum_direct_gap.value_ev,
        expected_gap["minimum_direct_gap"]["value_ev"],
        rel_tol=1e-9,
    )

    expected_manifest = json.loads(
        Path("tests/regression/expected/silicon_manifest.json").read_text(encoding="utf-8")
    )
    validate_schema_version(expected_manifest)
    manifest = RunManifest.model_validate(expected_manifest)
    assert manifest.is_usable_for_downstream() is True
