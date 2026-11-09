import pytest
from pydantic import ValidationError

from semidft.core.hashing import compute_input_hash, compute_structure_hash
from semidft.core.models import (
    CalculationSpec,
    CalculationType,
    CellType,
    ExecutionStatus,
    RunManifest,
    StructureRecord,
    ValidationStatus,
)
from semidft.core.schemas import CURRENT_SCHEMA_VERSION, validate_schema_version


def _make_si_structure() -> StructureRecord:
    return StructureRecord(
        material_id="silicon-diamond",
        formula="Si",
        lattice_matrix_angstrom=[
            [0.0, 2.715, 2.715],
            [2.715, 0.0, 2.715],
            [2.715, 2.715, 0.0],
        ],
        species=["Si", "Si"],
        fractional_coords=[[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]],
        space_group_symbol="Fd-3m",
        space_group_number=227,
        symprec_angstrom=1e-3,
        cell_type=CellType.PRIMITIVE,
    )


def test_orthogonal_execution_and_validation_status_spec_01() -> None:
    structure = _make_si_structure()
    spec = CalculationSpec(
        calculation_id="si-scf-001",
        material_id="silicon-diamond",
        calculation_type=CalculationType.SCF,
        xc_functional="PBE",
        pseudopotentials={"Si": "Si.UPF"},
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        conv_thr_ry=1.0e-8,
    )
    manifest = RunManifest(
        calculation_id=spec.calculation_id,
        material_id=spec.material_id,
        calculation_type=spec.calculation_type,
        execution_status=ExecutionStatus.COMPLETED,
        validation_status=ValidationStatus.UNCONVERGED,
        exit_code=0,
        structure_hash=compute_structure_hash(structure),
        input_hash="a" * 64,
        qe_version="7.5",
        xc_functional="PBE",
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        pseudo_checksums={"Si": "b" * 64},
    )
    assert manifest.execution_status == ExecutionStatus.COMPLETED
    assert manifest.validation_status == ValidationStatus.UNCONVERGED
    assert manifest.is_usable_for_downstream() is False

    converged_manifest = manifest.model_copy(
        update={"validation_status": ValidationStatus.CONVERGED}
    )
    assert converged_manifest.is_usable_for_downstream() is True


def test_structure_record_validates_shapes() -> None:
    with pytest.raises(ValidationError):
        StructureRecord(
            material_id="bad",
            formula="Si",
            lattice_matrix_angstrom=[[1.0, 0.0], [0.0, 1.0]],
            species=["Si"],
            fractional_coords=[[0.0, 0.0, 0.0]],
        )


def test_deterministic_input_hash_invariance() -> None:
    structure = _make_si_structure()
    spec = CalculationSpec(
        calculation_id="si-scf-001",
        material_id="silicon-diamond",
        calculation_type=CalculationType.SCF,
        xc_functional="PBE",
        pseudopotentials={"Ge": "Ge.UPF", "Si": "Si.UPF"},
        ecutwfc_ry=40.0,
        ecutrho_ry=320.0,
        kpoints=[8, 8, 8],
    )
    spec_reordered = CalculationSpec(
        calculation_id="si-scf-999",
        material_id="silicon-diamond",
        calculation_type=CalculationType.SCF,
        xc_functional="PBE",
        pseudopotentials={"Si": "Si.UPF", "Ge": "Ge.UPF"},
        ecutwfc_ry=40.0,
        ecutrho_ry=320.0,
        kpoints=[8, 8, 8],
    )
    h1 = compute_input_hash(structure, spec, {"Si": "111", "Ge": "222"}, qe_version="7.5")
    h2 = compute_input_hash(structure, spec_reordered, {"Ge": "222", "Si": "111"}, qe_version="7.5")
    assert h1 == h2
    assert len(h1) == 64


def test_schema_version_validation() -> None:
    payload = {"schema_version": CURRENT_SCHEMA_VERSION, "data": 1}
    assert validate_schema_version(payload) == CURRENT_SCHEMA_VERSION
    with pytest.raises(ValueError, match="Unsupported schema_version"):
        validate_schema_version({"schema_version": "99.0.0"})
