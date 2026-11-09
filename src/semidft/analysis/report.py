"""Markdown and JSON scientific report generator with explicit provenance and method attribution."""

import json
from typing import Any

from semidft.analysis.gap_classifier import ElectronicGapReport
from semidft.analysis.validation import ScientificValidationSummary
from semidft.core.models import RunManifest
from semidft.core.schemas import CURRENT_SCHEMA_VERSION


def generate_markdown_report(
    manifest: RunManifest,
    gap_report: ElectronicGapReport | None = None,
    validation: ScientificValidationSummary | None = None,
) -> str:
    """Render a reproducible Markdown scientific report separating DFT vs experimental values."""
    lines = [
        f"# Semiconductor DFT Report — `{manifest.material_id}` (`{manifest.calculation_id}`)",
        "",
        "## 1. Execution & Convergence Status",
        f"- **Execution Status:** `{manifest.execution_status.value}` "
        f"(Exit code: `{manifest.exit_code}`)",
        f"- **Validation Status:** `{manifest.validation_status.value}`",
        f"- **Quantum ESPRESSO Version:** `{manifest.qe_version}`",
        f"- **XC Functional:** `{manifest.xc_functional}`",
        f"- **Cutoffs:** `ecutwfc = {manifest.ecutwfc_ry} Ry`, "
        f"`ecutrho = {manifest.ecutrho_ry} Ry`",
        f"- **K-point Mesh:** `{manifest.kpoints}`",
        f"- **Input Hash (SHA-256):** `{manifest.input_hash}`",
        f"- **Total Energy:** `{manifest.total_energy_ev} eV`",
        "",
    ]

    if gap_report is not None:
        lines.extend(
            [
                "## 2. Electronic Structure & Band Gap Analysis",
                f"- **Kohn–Sham {gap_report.xc_functional} Fundamental Gap:** "
                f"`{gap_report.fundamental_gap.value_ev:.4f} eV` "
                f"(`{gap_report.gap_classification}`)",
                f"- **Minimum Direct Gap:** `{gap_report.minimum_direct_gap.value_ev:.4f} eV` "
                f"at k = `{gap_report.minimum_direct_gap.kpoint_fractional}`",
                f"- **VBM:** `{gap_report.fundamental_gap.vbm.energy_ev:.4f} eV` "
                f"at k = `{gap_report.fundamental_gap.vbm.kpoint_fractional}`",
                f"- **CBM:** `{gap_report.fundamental_gap.cbm.energy_ev:.4f} eV` "
                f"at k = `{gap_report.fundamental_gap.cbm.kpoint_fractional}`",
                f"- **Sampling Resolution:** `{gap_report.sampling.resolution_note}`",
            ]
        )
        if gap_report.experimental_reference_gap is not None:
            exp = gap_report.experimental_reference_gap
            lines.extend(
                [
                    "",
                    "### Experimental Reference Comparison",
                    f"- **Experimental Gap ({exp.temperature_k} K, {exp.phase}, "
                    f"{exp.gap_definition}):** "
                    f"`{exp.value_ev:.3f} eV` (± `{exp.uncertainty_ev} eV`)",
                    f"- **Reference Source:** {exp.source.citation} (DOI: `{exp.source.doi}`)",
                    f"- **Method Note:** {gap_report.systematic_error_note}",
                ]
            )
        lines.append("")

    if validation is not None:
        lines.extend(
            [
                "## 3. Method-Consistent PBE Validation Summary",
                f"- **PBE Lattice Agreement:** `{validation.pbe_lattice_agreed}` "
                f"(Δa0 = `{validation.pbe_lattice_diff_angstrom} Å`)",
                f"- **PBE Bulk Modulus Agreement:** `{validation.pbe_bulk_modulus_agreed}` "
                f"(ΔB0 = `{validation.pbe_bulk_modulus_diff_gpa} GPa`)",
                f"- **PBE Gap Agreement:** `{validation.pbe_gap_agreed}` "
                f"(ΔEg = `{validation.pbe_gap_diff_ev} eV`)",
                f"- **Band Topology Agreement:** `{validation.gap_topology_agreed}`",
                "",
            ]
        )

    return "\n".join(lines)


def generate_json_report(
    manifest: RunManifest,
    gap_report: ElectronicGapReport | None = None,
    validation: ScientificValidationSummary | None = None,
) -> str:
    """Render a schema-versioned JSON scientific report separating DFT vs experimental values."""
    payload: dict[str, Any] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "manifest": manifest.model_dump(),
        "gap_report": gap_report.model_dump() if gap_report is not None else None,
        "validation": validation.model_dump() if validation is not None else None,
    }
    return json.dumps(payload, indent=2)
