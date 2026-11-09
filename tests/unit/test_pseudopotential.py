from pathlib import Path

import pytest

from semidft.core.exceptions import PseudopotentialError
from semidft.pseudopotentials.catalog import load_pseudo_catalog
from semidft.pseudopotentials.metadata import PseudopotentialMetadata, parse_upf_header
from semidft.pseudopotentials.resolver import resolve_cutoffs
from semidft.pseudopotentials.validator import validate_pseudopotential_set

MINIMAL_SI_UPF_V2 = """<UPF version="2.0.1">
  <PP_HEADER
    element="Si"
    pseudo_type="USPP"
    relativistic="scalar"
    functional="PBE"
    z_valence="4.0"
    wfc_cutoff="30.0"
    rho_cutoff="240.0"
  />
</UPF>
"""


def test_parse_minimal_upf_v2_header(tmp_path: Path) -> None:
    upf = tmp_path / "Si.UPF"
    upf.write_text(MINIMAL_SI_UPF_V2, encoding="utf-8")

    meta = parse_upf_header(upf)
    assert meta.element == "Si"
    assert meta.functional == "PBE"
    assert meta.pseudo_type == "USPP"
    assert meta.relativistic == "scalar_relativistic"
    assert meta.recommended_ecutwfc_ry == 30.0
    assert meta.recommended_ecutrho_ry == 240.0
    assert len(meta.sha256 or "") == 64


def test_validator_rejects_mixed_xc_functionals() -> None:
    catalog = {
        "Ga": PseudopotentialMetadata(
            element="Ga",
            functional="PBE",
            pseudo_type="PAW",
            relativistic="scalar_relativistic",
            recommended_ecutwfc_ry=45.0,
            recommended_ecutrho_ry=360.0,
            filename="Ga.UPF",
        ),
        "As": PseudopotentialMetadata(
            element="As",
            functional="LDA",
            pseudo_type="PAW",
            relativistic="scalar_relativistic",
            recommended_ecutwfc_ry=40.0,
            recommended_ecutrho_ry=320.0,
            filename="As.UPF",
        ),
    }
    with pytest.raises(PseudopotentialError, match="Incompatible XC functional"):
        validate_pseudopotential_set(
            elements=["Ga", "As"],
            catalog=catalog,
            require_files=False,
            expected_xc="PBE",
        )


def test_resolve_cutoffs_takes_maximum_and_preserves_uspp_paw_dual() -> None:
    catalog = load_pseudo_catalog(Path("configs/pseudopotentials/sssp-pbe.yaml"))
    validated = validate_pseudopotential_set(
        elements=["Ga", "As"],
        catalog=catalog,
        require_files=False,
        expected_xc="PBE",
    )
    ecutwfc, ecutrho = resolve_cutoffs(validated)
    assert ecutwfc >= 40.0
    assert ecutrho >= 320.0
    assert ecutrho / ecutwfc == 8.0
