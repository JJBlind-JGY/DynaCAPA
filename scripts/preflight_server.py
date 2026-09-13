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
from typing import Any


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
    parser.add_argument("--require-training-stack", action="store_true")
    parser.add_argument("--min-gpus", type=int, default=1)
    parser.add_argument("--min-memory-gib", type=float, default=20.0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    disk = shutil.disk_usage(root)
    package_versions: dict[str, str | None] = {}
    checked_packages = (
        "pydantic",
        "PyYAML",
        "pytest",
        "hypothesis",
        "torch",
        "transformers",
        "trl",
        "datasets",
        "peft",
        "accelerate",
    )
    for package in checked_packages:
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = None

    torch_report: dict[str, Any] = {"available": False}
    try:
        import torch

        torch_report = {
            "available": True,
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
            "gpu_count": torch.cuda.device_count(),
            "bf16_supported": (
                torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False
            ),
            "nccl_version": (
                torch.cuda.nccl.version()
                if torch.cuda.is_available() and hasattr(torch.cuda, "nccl")
                else None
            ),
            "gpus": [
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "memory_gib": round(
                        torch.cuda.get_device_properties(index).total_memory / 1024**3,
                        2,
                    ),
                }
                for index in range(torch.cuda.device_count())
            ],
        }
    except ImportError:
        pass

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
        "nvcc": _command(["nvcc", "--version"]),
        "torch": torch_report,
        "packages": package_versions,
        "disk_free_gib": round(disk.free / 1024**3, 2),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    core_ok = bool(report["python"]["supported"] and report["git"]["available"])
    gpu_ok = bool(report["nvidia_smi"]["available"] or args.allow_no_gpu)
    if not args.allow_no_gpu and torch_report.get("available"):
        enough_gpus = int(torch_report.get("gpu_count", 0)) >= args.min_gpus
        enough_memory = all(
            gpu["memory_gib"] >= args.min_memory_gib
            for gpu in torch_report.get("gpus", [])[: args.min_gpus]
        )
        gpu_ok = bool(
            gpu_ok
            and torch_report.get("cuda_available")
            and enough_gpus
            and enough_memory
        )
    stack_ok = True
    if args.require_training_stack:
        stack_ok = all(
            package_versions[name] is not None
            for name in ("torch", "transformers", "trl", "datasets", "peft", "accelerate")
        )
    return 0 if core_ok and gpu_ok and stack_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
