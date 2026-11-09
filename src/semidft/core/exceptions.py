"""Domain-specific exception hierarchy for semidft."""


class SemiDFTError(Exception):
    """Base exception for all expected domain errors in semidft."""


class StructureValidationError(SemiDFTError):
    """Raised when a crystal structure violates physical or crystallographic invariants."""


class SymmetryAnalysisError(SemiDFTError):
    """Raised when space-group analysis or cell standardization fails."""


class PseudopotentialError(SemiDFTError):
    """Raised when a pseudopotential is missing, corrupt, or physically incompatible."""


class QEConfigurationError(SemiDFTError):
    """Raised when Quantum ESPRESSO executables, inputs, or hardware limits are invalid."""


class QEExecutionError(SemiDFTError):
    """Raised when a Quantum ESPRESSO process fails or terminates abnormally."""


class ConvergenceError(SemiDFTError):
    """Raised when a calculation completes execution but fails physical convergence criteria."""


class StorageConflictError(SemiDFTError):
    """Raised when an operation would overwrite immutable calculation artifacts."""
