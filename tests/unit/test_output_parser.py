import math

from semidft.core.units import RY_TO_EV
from semidft.engines.qe.output_parser import parse_pw_output

SAMPLE_PW_SCF_CONVERGED = """
     Program PWSCF v.7.5 starts on  9Nov2026 at 16:00:00
     convergence has been achieved in   6 iterations
!    total energy              =     -15.84420000 Ry
     estimated scf accuracy    <       0.0000000021 Ry
     the Fermi energy is     6.2540 ev
     Total force =     0.000000     Total SCF correction =     0.000000
     total   stress  (Ry/bohr**3)                   (kbar)     P=   -0.12
        -0.00000081   0.00000000   0.00000000         -0.12      0.00      0.00
         0.00000000  -0.00000081   0.00000000          0.00     -0.12      0.00
         0.00000000   0.00000000  -0.00000081          0.00      0.00     -0.12
     JOB DONE.
"""


def test_parse_pw_scf_output_converts_units() -> None:
    parsed = parse_pw_output(SAMPLE_PW_SCF_CONVERGED)
    assert parsed.job_done is True
    assert parsed.scf_converged_flag is True
    assert parsed.scf_iterations == 6
    assert math.isclose(parsed.total_energy_ev or 0.0, -15.8442 * RY_TO_EV, rel_tol=1e-9)
    assert math.isclose(parsed.fermi_energy_ev or 0.0, 6.2540, rel_tol=1e-9)
    assert math.isclose(parsed.pressure_gpa or 0.0, -0.012, rel_tol=1e-9)
