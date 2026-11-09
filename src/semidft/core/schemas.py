"""Schema versioning and compatibility checks for serialized JSON artifacts [SPEC-07]."""

from typing import Any

CURRENT_SCHEMA_VERSION: str = "1.0.0"
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({"1.0.0", "1"})


def validate_schema_version(payload: dict[str, Any]) -> str:
    """Validate that a deserialized JSON/YAML dict has a supported schema_version."""
    raw_version = str(payload.get("schema_version", CURRENT_SCHEMA_VERSION))
    if raw_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schema_version {raw_version!r}. "
            f"Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    return CURRENT_SCHEMA_VERSION
