from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dynacapa.training.readiness import (
    load_training_config,
    validate_training_readiness,
)


ROOT = Path(__file__).resolve().parents[2]


def test_sft_smoke_config_passes_local_structural_readiness() -> None:
    config = load_training_config(ROOT / "configs/sft/qwen3_0_6b_smoke.yaml")
    config = config.model_copy(
        update={"output_dir": f"outputs/readiness-probes/process-{os.getpid()}-sft"}
    )

    report = validate_training_readiness(
        ROOT,
        config,
        require_registry=False,
        require_dependency_lock=False,
    )

    assert report.ready is True
    assert report.checks["manifest_hash_matches"] is True
    assert report.checks["artifact_train_sft_hash_matches"] is True
    assert report.checks["artifact_validation_sft_hash_matches"] is True
    assert report.checks["frozen_test_sealed"] is True


def test_dpo_waits_for_exact_preceding_sft_adapter() -> None:
    config = load_training_config(ROOT / "configs/preference/qwen3_0_6b_smoke.yaml")
    config = config.model_copy(
        update={
            "output_dir": f"outputs/readiness-probes/process-{os.getpid()}-dpo",
            "model": config.model.model_copy(
                update={
                    "initial_adapter_path": (
                        f"outputs/readiness-probes/process-{os.getpid()}-missing-adapter"
                    )
                }
            ),
        }
    )

    report = validate_training_readiness(
        ROOT,
        config,
        require_registry=False,
        require_dependency_lock=False,
    )

    assert report.ready is False
    assert report.checks["initial_adapter_exists"] is False
    assert any("preceding SFT adapter" in blocker for blocker in report.blockers)


def test_manifest_hash_drift_fails_closed() -> None:
    config = load_training_config(ROOT / "configs/sft/qwen3_0_6b_smoke.yaml")
    tampered = config.model_copy(
        update={
            "data": config.data.model_copy(update={"manifest_sha256": "0" * 64})
        }
    )

    report = validate_training_readiness(
        ROOT,
        tampered,
        require_registry=False,
        require_dependency_lock=False,
    )

    assert report.ready is False
    assert report.checks["manifest_hash_matches"] is False


def test_smoke_artifact_cannot_be_relabelled_formal() -> None:
    config = load_training_config(ROOT / "configs/sft/qwen3_0_6b_smoke.yaml")
    formal = config.model_copy(update={"purpose": "formal"})

    report = validate_training_readiness(
        ROOT,
        formal,
        require_registry=False,
        require_dependency_lock=False,
    )

    assert report.ready is False
    assert report.checks["artifact_eligible_for_purpose"] is False


def test_paths_cannot_escape_repository() -> None:
    config = load_training_config(ROOT / "configs/sft/qwen3_0_6b_smoke.yaml")
    escaped = config.model_copy(update={"output_dir": "../outside"})

    with pytest.raises(ValueError, match="escapes repository root"):
        validate_training_readiness(
            ROOT,
            escaped,
            require_registry=False,
            require_dependency_lock=False,
        )


def test_generated_jsonl_matches_trl_conversational_shapes() -> None:
    manifest = json.loads(
        (ROOT / "data/manifests/dynacapa_mail_training_v0_2_minimal_v1.manifest.json").read_text(
            "utf-8"
        )
    )
    sft_path = ROOT / manifest["files"]["train_sft"]["path"]
    dpo_path = ROOT / manifest["files"]["train_dpo"]["path"]
    sft = json.loads(sft_path.read_text("utf-8").splitlines()[0])
    dpo = json.loads(dpo_path.read_text("utf-8").splitlines()[0])

    assert [message["role"] for message in sft["prompt"]] == ["system", "user"]
    assert [message["role"] for message in sft["completion"]] == ["assistant"]
    assert [message["role"] for message in dpo["prompt"]] == ["system", "user"]
    assert [message["role"] for message in dpo["chosen"]] == ["assistant"]
    assert [message["role"] for message in dpo["rejected"]] == ["assistant"]


def test_mixed_dpo_loss_is_explicit_and_aligned() -> None:
    config = load_training_config(
        ROOT
        / "configs/preference/qwen3_0_6b_balanced64_contrastive32_sftloss.yaml"
    )
    assert config.trainer.loss_type == ("sigmoid", "sft")
    assert config.trainer.loss_weights == (1.0, 1.0)
