from semidft.core.models import CalculationSpec, CalculationType, ValidationStatus
from semidft.engines.qe.convergence.validation import evaluate_calculation_convergence
from semidft.engines.qe.output_parser import ParsedPWOutput


def _base_spec(calc_type: CalculationType) -> CalculationSpec:
    return CalculationSpec(
        calculation_id=f"si-{calc_type.value}-001",
        material_id="silicon-diamond",
        calculation_type=calc_type,
        pseudopotentials={"Si": "Si.UPF"},
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        conv_thr_ry=1e-8,
        energy_tolerance_ev=1.36e-3,
        force_tolerance_ev_per_angstrom=0.01,
        pressure_tolerance_gpa=0.05,
        stress_tolerance_gpa=0.08,
    )


def test_scf_convergence_distinguishes_completed_vs_unconverged_spec_01_02() -> None:
    spec = _base_spec(CalculationType.SCF)
    unconverged_out = ParsedPWOutput(
        job_done=True,
        scf_converged_flag=False,
        total_energy_ev=-215.5,
        estimated_scf_accuracy_ry=1e-4,
    )
    status, summary = evaluate_calculation_convergence(spec, unconverged_out)
    assert status == ValidationStatus.UNCONVERGED
    assert summary.electronic_converged is False


def test_nscf_and_bands_do_not_require_scf_loop_marker_spec_02() -> None:
    for ctype in (CalculationType.NSCF, CalculationType.BANDS):
        spec = _base_spec(ctype)
        parsed = ParsedPWOutput(
            job_done=True,
            scf_converged_flag=False,
            num_kpoints_computed=29,
            eigenvalues_ev=[[0.0, 1.0, 2.0, 3.0]],
        )
        status, summary = evaluate_calculation_convergence(spec, parsed)
        assert status == ValidationStatus.CONVERGED
        assert summary.electronic_converged is True


def test_vc_relax_checks_ionic_force_energy_pressure_and_stress_tensor_spec_02() -> None:
    spec = _base_spec(CalculationType.VC_RELAX)
    converged_vcrelax = ParsedPWOutput(
        job_done=True,
        scf_converged_flag=True,
        bfgs_converged_flag=True,
        total_energy_ev=-215.56,
        final_energy_change_ev=0.0002,
        max_force_ev_per_angstrom=0.003,
        pressure_gpa=0.01,
        max_stress_component_gpa=0.02,
    )
    status, summary = evaluate_calculation_convergence(spec, converged_vcrelax)
    assert status == ValidationStatus.CONVERGED
    assert summary.ionic_converged is True
    assert summary.cell_converged is True

    high_stress_tensor = converged_vcrelax.model_copy(update={"max_stress_component_gpa": 0.25})
    status_bad, _ = evaluate_calculation_convergence(spec, high_stress_tensor)
    assert status_bad == ValidationStatus.UNCONVERGED
