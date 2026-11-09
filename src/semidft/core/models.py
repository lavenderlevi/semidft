"""Canonical Pydantic v2 models for structures, calculations, and manifests."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from semidft.core.schemas import CURRENT_SCHEMA_VERSION


class ExecutionStatus(StrEnum):
    """Process execution lifecycle status, independent of physical convergence [SPEC-01]."""

    CREATED = "CREATED"
    PREPARED = "PREPARED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class ValidationStatus(StrEnum):
    """Scientific and numerical validation status [SPEC-01]."""

    NOT_EVALUATED = "NOT_EVALUATED"
    CONVERGED = "CONVERGED"
    UNCONVERGED = "UNCONVERGED"
    PARSE_FAILED = "PARSE_FAILED"


class CalculationType(StrEnum):
    """Supported Quantum ESPRESSO calculation types."""

    SCF = "scf"
    NSCF = "nscf"
    BANDS = "bands"
    RELAX = "relax"
    VC_RELAX = "vc-relax"
    DOS = "dos"


class CellType(StrEnum):
    """Crystallographic cell classification."""

    ORIGINAL = "original"
    PRIMITIVE = "primitive"
    CONVENTIONAL = "conventional"
    SUPERCELL = "supercell"
    RELAXED = "relaxed"


class TransformationStep(BaseModel):
    """Records a deterministic lattice/cell transformation step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: str
    transformation_matrix: list[list[float]]
    determinant: float
    symprec_angstrom: float | None = None
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="after")
    def _check_matrix_shape(self) -> "TransformationStep":
        if len(self.transformation_matrix) != 3 or any(
            len(row) != 3 for row in self.transformation_matrix
        ):
            raise ValueError("transformation_matrix must have shape 3x3")
        return self


class StructureRecord(BaseModel):
    """Canonical crystal structure representation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = CURRENT_SCHEMA_VERSION
    material_id: str
    formula: str
    lattice_matrix_angstrom: list[list[float]]
    species: list[str]
    fractional_coords: list[list[float]]
    space_group_symbol: str | None = None
    space_group_number: int | None = None
    symprec_angstrom: float | None = None
    cell_type: CellType = CellType.ORIGINAL
    source_file: str | None = None
    source_format: str | None = "cif"
    transformation_history: list[TransformationStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_structure_invariants(self) -> "StructureRecord":
        if len(self.lattice_matrix_angstrom) != 3 or any(
            len(row) != 3 for row in self.lattice_matrix_angstrom
        ):
            raise ValueError("lattice_matrix_angstrom must have shape 3x3")
        if not self.species:
            raise ValueError("StructureRecord must contain at least one atomic site")
        if len(self.species) != len(self.fractional_coords):
            raise ValueError(
                f"species length ({len(self.species)}) != fractional_coords length "
                f"({len(self.fractional_coords)})"
            )
        if any(len(coord) != 3 for coord in self.fractional_coords):
            raise ValueError("Each fractional coordinate must have length 3")
        return self


class CalculationSpec(BaseModel):
    """Specification for a single Quantum ESPRESSO calculation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = CURRENT_SCHEMA_VERSION
    calculation_id: str
    material_id: str
    calculation_type: CalculationType
    xc_functional: str = "PBE"
    pseudopotentials: dict[str, str]
    ecutwfc_ry: float
    ecutrho_ry: float
    kpoints: list[int] = Field(default_factory=lambda: [8, 8, 8])
    kpoint_offset: list[int] = Field(default_factory=lambda: [0, 0, 0])
    conv_thr_ry: float = 1.0e-8
    energy_tolerance_ev: float = 1.3605693122994e-3
    force_tolerance_ev_per_angstrom: float = 0.01
    pressure_tolerance_gpa: float = 0.05
    stress_tolerance_gpa: float | None = None
    occupations: Literal["fixed", "smearing", "tetrahedra"] = "fixed"
    smearing_type: Literal["gaussian", "cold", "mp", "fd"] | None = None
    degauss_ry: float | None = None
    nbnd: int | None = None
    spin_mode: Literal["non_spin_polarized", "collinear", "noncollinear_soc"] = "non_spin_polarized"
    nstep: int = 100
    electron_maxstep: int = 100
    disk_io: Literal["low", "medium", "high", "nowf"] = "low"
    execution_backend: Literal["cpu_hybrid", "rocm_igpu"] = "cpu_hybrid"
    mpi_ranks: int | None = None
    npool: int | None = None
    omp_threads: int | None = None

    @model_validator(mode="after")
    def _validate_numerical_parameters(self) -> "CalculationSpec":
        if self.ecutwfc_ry <= 0 or self.ecutrho_ry <= 0:
            raise ValueError("ecutwfc_ry and ecutrho_ry must be strictly positive")
        if self.ecutrho_ry < self.ecutwfc_ry:
            raise ValueError("ecutrho_ry must be >= ecutwfc_ry")
        if len(self.kpoints) != 3 or any(k <= 0 for k in self.kpoints):
            raise ValueError("kpoints must be a list of 3 positive integers")
        if len(self.kpoint_offset) != 3 or any(k not in (0, 1) for k in self.kpoint_offset):
            raise ValueError("kpoint_offset must be a list of 3 values in {0, 1}")
        return self


class RunManifest(BaseModel):
    """Immutable provenance record for a calculation directory [SPEC-01, SPEC-07]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = CURRENT_SCHEMA_VERSION
    calculation_id: str
    material_id: str
    calculation_type: CalculationType
    execution_status: ExecutionStatus = ExecutionStatus.CREATED
    validation_status: ValidationStatus = ValidationStatus.NOT_EVALUATED
    exit_code: int | None = None
    validation_messages: list[str] = Field(default_factory=list)
    structure_hash: str
    input_hash: str
    qe_version: str
    xc_functional: str
    ecutwfc_ry: float
    ecutrho_ry: float
    kpoints: list[int]
    pseudo_checksums: dict[str, str]
    total_energy_ev: float | None = None
    fermi_energy_ev: float | None = None
    max_force_ev_per_angstrom: float | None = None
    pressure_gpa: float | None = None
    wall_time_seconds: float | None = None
    created_at_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_usable_for_downstream(self) -> bool:
        """Return True iff the calculation both completed execution and converged physically."""
        return (
            self.execution_status == ExecutionStatus.COMPLETED
            and self.validation_status == ValidationStatus.CONVERGED
        )
