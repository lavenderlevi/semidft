"""Unit tests for SQLite provenance index and CLI subcommands (pseudo, calc, workflow, results)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from semidft.cli.app import app
from semidft.core.models import (
    CalculationType,
    ExecutionStatus,
    RunManifest,
    ValidationStatus,
)
from semidft.storage.database import ProvenanceDatabase


def test_sqlite_provenance_index_upserts_and_queries_by_hash(tmp_path: Path) -> None:
    db = ProvenanceDatabase(tmp_path / "index.sqlite")
    manifest = RunManifest(
        calculation_id="si-scf-001",
        material_id="silicon-diamond",
        calculation_type=CalculationType.SCF,
        execution_status=ExecutionStatus.COMPLETED,
        validation_status=ValidationStatus.CONVERGED,
        exit_code=0,
        structure_hash="s" * 64,
        input_hash="h" * 64,
        qe_version="7.5",
        xc_functional="PBE",
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        pseudo_checksums={"Si": "p" * 64},
        total_energy_ev=-215.56,
    )
    db.upsert_manifest(manifest, tmp_path / "silicon-diamond/runs/si-scf-001")

    rec = db.get_manifest_record("si-scf-001")
    assert rec is not None
    assert rec["execution_status"] == "COMPLETED"
    assert rec["validation_status"] == "CONVERGED"

    by_hash = db.find_by_input_hash("h" * 64)
    assert len(by_hash) == 1
    assert by_hash[0]["calculation_id"] == "si-scf-001"

    all_rows = db.list_calculations()
    assert len(all_rows) == 1


def test_cli_pseudo_and_subcommands_registered() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["pseudo", "inspect", "Si", "--json"])
    assert res.exit_code == 0
    assert '"element": "Si"' in res.stdout

    res_check = runner.invoke(app, ["pseudo", "check-material", "GaAs", "--json"])
    assert res_check.exit_code == 0
    payload = json.loads(res_check.stdout)
    assert payload["material"] == "GaAs"
    assert payload["ecutwfc_ry"] == 45.0
    assert payload["ecutrho_ry"] == 360.0

    res_val = runner.invoke(
        app,
        [
            "pseudo",
            "validate",
            "--elements",
            "Si,Ga,As",
            "--pseudo-dir",
            "tests/fixtures/pseudos",
            "--json",
        ],
    )
    assert res_val.exit_code == 0
    val_payload = json.loads(res_val.stdout)
    assert val_payload["valid"] is True


def test_cli_doctor_benchmark_flag() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["doctor", "--benchmark", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert "benchmark_profiles" in payload
    profiles = payload["benchmark_profiles"]
    assert "cpu_hybrid_kpool" in profiles
    assert "cpu_hybrid_low_mem" in profiles
    assert "rocm_igpu" in profiles


def test_cli_calc_workflow_and_results_commands(tmp_path: Path) -> None:
    runner = CliRunner()

    # 1. Initialize calculation
    res_init = runner.invoke(
        app,
        [
            "calc",
            "init",
            "Si",
            "--type",
            "scf",
            "--calc-id",
            "si-scf-cli-001",
            "--base-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert res_init.exit_code == 0
    init_data = json.loads(res_init.stdout)
    assert init_data["calculation_id"] == "si-scf-cli-001"
    assert init_data["execution_status"] == "CREATED"

    # 2. Validate calculation
    res_val = runner.invoke(
        app,
        [
            "calc",
            "validate",
            "si-scf-cli-001",
            "--base-dir",
            str(tmp_path),
            "--pseudo-dir",
            "tests/fixtures/pseudos",
            "--json",
        ],
    )
    assert res_val.exit_code == 0
    val_data = json.loads(res_val.stdout)
    assert val_data["valid"] is True

    # 3. Prepare QE input
    res_prep = runner.invoke(
        app,
        [
            "calc",
            "prepare",
            "si-scf-cli-001",
            "--base-dir",
            str(tmp_path),
            "--pseudo-dir",
            "tests/fixtures/pseudos",
            "--json",
        ],
    )
    assert res_prep.exit_code == 0
    prep_data = json.loads(res_prep.stdout)
    assert prep_data["execution_status"] == "PREPARED"
    assert Path(prep_data["pw_in_path"]).is_file()

    # 4. Status check
    res_status = runner.invoke(
        app,
        ["calc", "status", "si-scf-cli-001", "--base-dir", str(tmp_path), "--json"],
    )
    assert res_status.exit_code == 0
    status_data = json.loads(res_status.stdout)
    assert status_data["execution_status"] == "PREPARED"
    assert status_data["validation_status"] == "NOT_EVALUATED"

    # 5. Workflow dry-run
    res_wf = runner.invoke(
        app,
        [
            "workflow",
            "run",
            "silicon-basic",
            "--dry-run",
            "--base-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert res_wf.exit_code == 0
    wf_data = json.loads(res_wf.stdout)
    assert wf_data["workflow"] == "silicon-basic"
    assert wf_data["dry_run"] is True

    # 6. Results report on calculation
    res_rep = runner.invoke(
        app,
        ["results", "report", "si-scf-cli-001", "--base-dir", str(tmp_path), "--json"],
    )
    assert res_rep.exit_code == 0
    rep_data = json.loads(res_rep.stdout)
    assert rep_data["manifest"]["calculation_id"] == "si-scf-cli-001"
