"""Write one immutable JSON trajectory per run/task pair."""

from __future__ import annotations

import json
from pathlib import Path

from dynacapa.core.schemas import Trajectory


class TrajectoryLogger:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write(self, trajectory: Trajectory) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{trajectory.run_id}__{trajectory.task_id}.json"
        if path.exists():
            raise FileExistsError(f"refusing to overwrite trajectory: {path}")
        path.write_text(
            json.dumps(trajectory.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

