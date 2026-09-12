"""Read-only platform preflight for Windows development and Linux training."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _command(command: list[str]) -> dict[str, object]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "output": None}
    completed = subprocess.run(
        [executable, *command[1:]],
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )
    return {
        "available": completed.returncode == 0,
        "output": (completed.stdout or completed.stderr).strip()[:4000],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-no-gpu", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    disk = shutil.disk_usage(root)
    package_versions: dict[str, str | None] = {}
    for package in ("pydantic", "PyYAML", "pytest", "hypothesis"):
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = None

    report = {
        "python": {
            "version": platform.python_version(),
            "supported": sys.version_info[:2] == (3, 11),
            "executable": sys.executable,
        },
        "platform": platform.platform(),
        "git": _command(["git", "--version"]),
        "nvidia_smi": _command(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]
        ),
        "packages": package_versions,
        "disk_free_gib": round(disk.free / 1024**3, 2),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    core_ok = bool(report["python"]["supported"] and report["git"]["available"])
    gpu_ok = bool(report["nvidia_smi"]["available"] or args.allow_no_gpu)
    return 0 if core_ok and gpu_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

