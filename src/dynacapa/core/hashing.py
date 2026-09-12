"""Canonical hashes for version-bound environment states."""

from __future__ import annotations

import hashlib
import json


def compose_state_hash(
    environment_state_hash: str,
    authorization_version: int,
    tool_versions: dict[str, str],
) -> str:
    canonical = json.dumps(
        {
            "environment_state_hash": environment_state_hash,
            "authorization_version": authorization_version,
            "tool_versions": tool_versions,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

