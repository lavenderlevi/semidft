"""Cutoff resolution from validated pseudopotential sets [SPEC-02]."""

from semidft.core.exceptions import PseudopotentialError
from semidft.pseudopotentials.metadata import PseudopotentialMetadata


def resolve_cutoffs(
    validated_pseudos: dict[str, PseudopotentialMetadata],
    ecutwfc_override_ry: float | None = None,
    ecutrho_override_ry: float | None = None,
) -> tuple[float, float]:
    """Resolve (ecutwfc_ry, ecutrho_ry) pair without guessing missing cutoffs."""
    if not validated_pseudos:
        raise PseudopotentialError("Cannot resolve cutoffs from an empty pseudopotential set.")

    max_wfc = 0.0
    max_rho = 0.0
    max_dual = 4.0

    for el, meta in validated_pseudos.items():
        if ecutwfc_override_ry is None and meta.recommended_ecutwfc_ry is None:
            raise PseudopotentialError(
                f"Pseudopotential for {el} has no recommended_ecutwfc_ry and no override was given."
            )
        if ecutrho_override_ry is None and meta.recommended_ecutrho_ry is None:
            raise PseudopotentialError(
                f"Pseudopotential for {el} has no recommended_ecutrho_ry and no override was given."
            )
        if meta.recommended_ecutwfc_ry is not None:
            max_wfc = max(max_wfc, meta.recommended_ecutwfc_ry)
        if meta.recommended_ecutrho_ry is not None:
            max_rho = max(max_rho, meta.recommended_ecutrho_ry)
        max_dual = max(max_dual, meta.dual_ratio)

    resolved_wfc = float(ecutwfc_override_ry) if ecutwfc_override_ry is not None else max_wfc
    if ecutrho_override_ry is not None:
        resolved_rho = float(ecutrho_override_ry)
    elif ecutwfc_override_ry is not None:
        resolved_rho = resolved_wfc * max_dual
    else:
        resolved_rho = max_rho

    return (resolved_wfc, resolved_rho)
