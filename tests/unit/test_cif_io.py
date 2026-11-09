from pathlib import Path

from semidft.core.models import CellType
from semidft.structures.builder import build_reference_structure
from semidft.structures.cif_io import read_cif, structure_record_to_ase, write_cif


def test_cif_round_trip_preserves_silicon_primitive(tmp_path: Path) -> None:
    si = build_reference_structure("Si", cell_type=CellType.PRIMITIVE)
    assert len(si.species) == 2
    assert si.formula == "Si"

    cif_path = tmp_path / "Si_test.cif"
    write_cif(si, cif_path)
    loaded = read_cif(cif_path, material_id="si-loaded")

    assert loaded.formula == "Si"
    assert len(loaded.species) == 2
    atoms = structure_record_to_ase(loaded)
    assert len(atoms) == 2
    assert list(atoms.get_chemical_symbols()) == ["Si", "Si"]  # type: ignore[no-untyped-call]
