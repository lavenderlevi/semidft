"""Focused UPF v1/v2 header parser and PseudopotentialMetadata model."""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from semidft.core.exceptions import PseudopotentialError
from semidft.core.hashing import compute_file_sha256


class PseudopotentialMetadata(BaseModel):
    """Validated metadata for a single element's UPF pseudopotential."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    element: str
    functional: str
    pseudo_type: Literal["NC", "USPP", "PAW"]
    relativistic: Literal["scalar_relativistic", "full_relativistic", "non_relativistic"]
    z_valence: float = 4.0
    source: str = "SSSP"
    library_version: str = "2.0"
    recommended_ecutwfc_ry: float | None = None
    recommended_ecutrho_ry: float | None = None
    filename: str
    sha256: str | None = None

    @property
    def dual_ratio(self) -> float:
        """Return ecutrho / ecutwfc ratio based on metadata or pseudo_type."""
        if (
            self.recommended_ecutwfc_ry
            and self.recommended_ecutrho_ry
            and self.recommended_ecutwfc_ry > 0
        ):
            return self.recommended_ecutrho_ry / self.recommended_ecutwfc_ry
        return 4.0 if self.pseudo_type == "NC" else 8.0


def _extract_attr(header_text: str, attr_name: str) -> str | None:
    match = re.search(rf'{attr_name}\s*=\s*"([^"]+)"', header_text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_upf_header(path: Path) -> PseudopotentialMetadata:
    """Parse essential header metadata from a UPF v2 XML file."""
    if not path.is_file():
        raise PseudopotentialError(f"UPF file not found: {path}")

    head_chunk = path.read_text(encoding="utf-8", errors="ignore")[:16384]
    element = _extract_attr(head_chunk, "element")
    if not element:
        raise PseudopotentialError(f"Could not parse element from UPF header in {path.name}")

    raw_func = (_extract_attr(head_chunk, "functional") or "PBE").upper()
    functional = "PBESOL" if "PBESOL" in raw_func else ("PBE" if "PBE" in raw_func else raw_func)

    raw_type = (_extract_attr(head_chunk, "pseudo_type") or "NC").upper()
    if "PAW" in raw_type:
        pseudo_type: Literal["NC", "USPP", "PAW"] = "PAW"
    elif "US" in raw_type:
        pseudo_type = "USPP"
    else:
        pseudo_type = "NC"

    raw_rel = (_extract_attr(head_chunk, "relativistic") or "scalar").lower()
    if "full" in raw_rel:
        relativistic: Literal["scalar_relativistic", "full_relativistic", "non_relativistic"] = (
            "full_relativistic"
        )
    elif "no" in raw_rel:
        relativistic = "non_relativistic"
    else:
        relativistic = "scalar_relativistic"

    z_val_str = _extract_attr(head_chunk, "z_valence")
    wfc_str = _extract_attr(head_chunk, "wfc_cutoff")
    rho_str = _extract_attr(head_chunk, "rho_cutoff")

    return PseudopotentialMetadata(
        element=element.strip(),
        functional=functional,
        pseudo_type=pseudo_type,
        relativistic=relativistic,
        z_valence=float(z_val_str) if z_val_str else 4.0,
        recommended_ecutwfc_ry=float(wfc_str) if wfc_str and float(wfc_str) > 0 else None,
        recommended_ecutrho_ry=float(rho_str) if rho_str and float(rho_str) > 0 else None,
        filename=path.name,
        sha256=compute_file_sha256(path),
    )
