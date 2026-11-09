"""Physical consistency and integrity validation for pseudopotential sets."""

from pathlib import Path

from semidft.core.exceptions import PseudopotentialError
from semidft.core.hashing import compute_file_sha256
from semidft.pseudopotentials.metadata import PseudopotentialMetadata, parse_upf_header


def validate_pseudopotential_set(
    elements: list[str],
    catalog: dict[str, PseudopotentialMetadata],
    pseudo_dir: Path | None = None,
    require_files: bool = True,
    expected_xc: str = "PBE",
    spin_orbit: bool = False,
) -> dict[str, PseudopotentialMetadata]:
    """Validate element coverage, XC compatibility, relativistic mode, and file SHA-256."""
    unique_elements = sorted(set(elements))
    validated: dict[str, PseudopotentialMetadata] = {}

    for el in unique_elements:
        if el not in catalog:
            raise PseudopotentialError(f"Missing pseudopotential metadata for element {el!r}")

        meta = catalog[el]
        if meta.functional.upper() != expected_xc.upper():
            raise PseudopotentialError(
                f"Incompatible XC functional for {el}: expected {expected_xc!r}, "
                f"got {meta.functional!r} [AGENTS.md §6.2]."
            )

        if spin_orbit and meta.relativistic != "full_relativistic":
            raise PseudopotentialError(
                f"Spin-orbit coupling requires full_relativistic UPF for {el}, "
                f"got {meta.relativistic!r}."
            )

        if require_files:
            if pseudo_dir is None:
                raise PseudopotentialError("pseudo_dir is required when require_files=True")
            upf_path = pseudo_dir / meta.filename
            if not upf_path.is_file():
                raise PseudopotentialError(f"Pseudopotential file missing on disk: {upf_path}")
            parsed_header = parse_upf_header(upf_path)
            if parsed_header.element != el:
                raise PseudopotentialError(
                    f"Element mismatch in {upf_path.name}: "
                    f"expected {el}, found {parsed_header.element}"
                )
            actual_sha = compute_file_sha256(upf_path)
            if meta.sha256 and meta.sha256 != actual_sha:
                raise PseudopotentialError(
                    f"SHA-256 checksum mismatch for {upf_path.name}: "
                    f"expected {meta.sha256}, got {actual_sha}"
                )
            meta = meta.model_copy(update={"sha256": actual_sha})

        validated[el] = meta

    return validated
