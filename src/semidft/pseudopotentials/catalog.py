"""Catalog loader for curated pseudopotential libraries (e.g. SSSP PBE v2.0)."""

from pathlib import Path

import yaml

from semidft.core.exceptions import PseudopotentialError
from semidft.pseudopotentials.metadata import PseudopotentialMetadata


def load_pseudo_catalog(yaml_path: Path) -> dict[str, PseudopotentialMetadata]:
    """Load element -> PseudopotentialMetadata mapping from a YAML catalog."""
    if not yaml_path.is_file():
        raise PseudopotentialError(f"Pseudopotential catalog not found: {yaml_path}")

    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    elements_dict = raw.get("elements", {})
    catalog: dict[str, PseudopotentialMetadata] = {}
    for el, entry in elements_dict.items():
        catalog[str(el)] = PseudopotentialMetadata.model_validate(entry)
    return catalog
