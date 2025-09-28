"""Setup helper for the MusicPlayer application.

This script bootstraps a local virtual environment and installs the project's
runtime dependencies listed in ``requirements.txt``.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS_FILE = ROOT / "requirements.txt"


def create_venv() -> None:
    """Create a virtual environment if it does not already exist."""
    if VENV_DIR.exists():
        return
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])


def install_requirements() -> None:
    """Install dependencies into the virtual environment."""
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    venv_python = VENV_DIR / scripts_dir / ("python.exe" if os.name == "nt" else "python")
    if not venv_python.exists():
        raise RuntimeError("Virtual environment appears corrupted; missing Python executable.")

    subprocess.check_call([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])


def main() -> None:
    create_venv()
    install_requirements()
    print("Virtual environment ready. Use run.bat or run.sh to launch Localify.")


if __name__ == "__main__":
    main()
