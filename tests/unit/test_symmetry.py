from typer.testing import CliRunner

from semidft.cli.app import app
from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure
from semidft.structures.standardization import standardize_structure
from semidft.structures.symmetry import analyze_symmetry


def test_silicon_symmetry_and_standardization() -> None:
    si_conv = build_reference_structure("Si", cell_type=CellType.CONVENTIONAL)
    assert len(si_conv.species) == 8

    sym = analyze_symmetry(si_conv, symprec_angstrom=1e-3)
    assert sym.space_group_number == 227
    assert sym.space_group_symbol == "Fd-3m"
    assert sym.crystal_system == "cubic"

    si_prim = standardize_structure(si_conv, target="primitive", symprec_angstrom=1e-3)
    assert len(si_prim.species) == 2
    assert si_prim.cell_type == CellType.PRIMITIVE
    assert len(si_prim.transformation_history) == 1

    si_back = standardize_structure(si_prim, target="conventional", symprec_angstrom=1e-3)
    assert len(si_back.species) == 8
    assert si_back.cell_type == CellType.CONVENTIONAL


def test_ge_and_gaas_space_groups() -> None:
    ge = build_reference_structure("Ge", cell_type=CellType.PRIMITIVE)
    gaas = build_reference_structure("GaAs", cell_type=CellType.PRIMITIVE)

    assert analyze_symmetry(ge).space_group_number == 227
    gaas_sym = analyze_symmetry(gaas)
    assert gaas_sym.space_group_number == 216
    assert gaas_sym.space_group_symbol == "F-43m"


def test_structure_cli_inspect_and_symmetry() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["structure", "inspect", "Si", "--json"])
    assert res.exit_code == 0
    assert '"formula": "Si"' in res.stdout

    sym_res = runner.invoke(app, ["structure", "symmetry", "GaAs", "--json"])
    assert sym_res.exit_code == 0
    assert '"space_group_number": 216' in sym_res.stdout
