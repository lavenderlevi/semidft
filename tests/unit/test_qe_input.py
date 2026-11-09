from pathlib import Path

from semidft.core.models import CalculationSpec, CalculationType, CellType
from semidft.core.units import force_ev_ang_to_forc_conv_thr_ry_bohr
from semidft.engines.qe.input_generator import (
    generate_bands_x_input,
    generate_dos_x_input,
    generate_pw_input,
)
from semidft.structures.builder import build_reference_structure


def test_generate_pw_input_vc_relax_includes_converted_thresholds_spec_02() -> None:
    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    spec = CalculationSpec(
        calculation_id="si-vcrelax-001",
        material_id="silicon-diamond",
        calculation_type=CalculationType.VC_RELAX,
        xc_functional="PBE",
        pseudopotentials={"Si": "Si.UPF"},
        ecutwfc_ry=30.0,
        ecutrho_ry=240.0,
        kpoints=[8, 8, 8],
        energy_tolerance_ev=1.3605693122994e-3,  # 1e-4 Ry
        force_tolerance_ev_per_angstrom=0.01,  # ~3.88938076e-4 Ry/Bohr
        pressure_tolerance_gpa=0.05,  # 0.5 kbar
    )
    pw_text = generate_pw_input(si, spec)
    expected_forc_str = f"forc_conv_thr = {force_ev_ang_to_forc_conv_thr_ry_bohr(0.01):.8e}"
    assert "calculation = 'vc-relax'" in pw_text
    assert "etot_conv_thr = 1.00000000e-04" in pw_text
    assert expected_forc_str in pw_text
    assert "forc_conv_thr = 3.88938076e-04" in pw_text
    assert "press_conv_thr = 0.500000" in pw_text
    assert "CELL_PARAMETERS angstrom" in pw_text
    assert "ATOMIC_POSITIONS crystal" in pw_text
    assert "K_POINTS automatic" in pw_text


def test_generate_bands_and_dos_postproc_inputs() -> None:
    bands_in = generate_bands_x_input(prefix="si", outdir=Path("./scratch"), filband="bands.dat")
    assert "&BANDS" in bands_in
    assert "filband = 'bands.dat'" in bands_in

    dos_in = generate_dos_x_input(prefix="si", outdir=Path("./scratch"), fildos="si.dos")
    assert "&DOS" in dos_in
    assert "fildos = 'si.dos'" in dos_in
