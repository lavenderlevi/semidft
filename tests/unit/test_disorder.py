from pathlib import Path

import pytest

from semidft.core.exceptions import StructureValidationError
from semidft.structures.cif_io import read_cif

DISORDERED_CIF = """data_SiGe_disordered
_cell_length_a   5.5000
_cell_length_b   5.5000
_cell_length_c   5.5000
_cell_angle_alpha 90.0
_cell_angle_beta  90.0
_cell_angle_gamma 90.0
_symmetry_space_group_name_H-M 'P 1'
loop_
 _atom_site_label
 _atom_site_type_symbol
 _atom_site_fract_x
 _atom_site_fract_y
 _atom_site_fract_z
 _atom_site_occupancy
 Si1 Si 0.0 0.0 0.0 0.5
 Ge1 Ge 0.0 0.0 0.0 0.5
"""


def test_read_cif_rejects_disordered_occupancy(tmp_path: Path) -> None:
    cif_file = tmp_path / "disordered.cif"
    cif_file.write_text(DISORDERED_CIF, encoding="utf-8")
    with pytest.raises(StructureValidationError, match="Disordered or partially occupied"):
        read_cif(cif_file)
