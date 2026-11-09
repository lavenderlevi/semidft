"""Discovery and version probing for Quantum ESPRESSO and MPI binaries."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class QEExecutables(BaseModel):
    """Resolved paths and detected version for Quantum ESPRESSO and MPI."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pw_path: str | None = None
    bands_path: str | None = None
    dos_path: str | None = None
    pp_path: str | None = None
    mpirun_path: str | None = None
    qe_version: str | None = None


def _resolve_binary(name: str) -> str | None:
    """Locate a QE executable via SEMIDFT_QE_BIN_DIR, Pixi env, sibling QE dir, or PATH."""
    env_dir = os.environ.get("SEMIDFT_QE_BIN_DIR")
    candidate_dirs: list[Path] = []
    if env_dir:
        candidate_dirs.append(Path(env_dir))
    candidate_dirs.extend(
        [
            Path(".pixi/envs/default/bin"),
            Path("../qe-7.5-ReleasePack/qe-7.5/bin"),
            Path("../qe-7.5-ReleasePack/qe-7.5/build/bin"),
        ]
    )
    for d in candidate_dirs:
        cand = d / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand.resolve())
    return shutil.which(name)


def probe_qe_version(pw_executable: str | None) -> str | None:
    """Attempt to detect Quantum ESPRESSO version from pw.x startup header."""
    if not pw_executable or not Path(pw_executable).is_file():
        return None
    try:
        proc = subprocess.run(
            [pw_executable],
            input="",
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
        combined = f"{proc.stdout}\n{proc.stderr}"
        match = re.search(r"v\.?\s*(\d+\.\d+(?:\.\d+)?)", combined, re.IGNORECASE)
        if match:
            return match.group(1)
    except (OSError, subprocess.SubprocessError):
        return None
    return "unknown"


def discover_qe_executables() -> QEExecutables:
    """Locate pw.x, bands.x, dos.x, pp.x, and mpirun across configured search paths."""
    pw = _resolve_binary("pw.x")
    bands = _resolve_binary("bands.x")
    dos = _resolve_binary("dos.x")
    pp = _resolve_binary("pp.x")
    mpirun = shutil.which("mpirun")
    return QEExecutables(
        pw_path=pw,
        bands_path=bands,
        dos_path=dos,
        pp_path=pp,
        mpirun_path=mpirun,
        qe_version=probe_qe_version(pw),
    )
