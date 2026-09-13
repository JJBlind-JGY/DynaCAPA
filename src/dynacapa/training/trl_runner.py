"""Lazy TRL launcher. GPU libraries are imported only after readiness passes."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dynacapa.training.config import TrainingRunConfig
from dynacapa.training.readiness import validate_training_readiness


def execute_training(root: Path, config: TrainingRunConfig, config_path: Path) -> Path:
    report = validate_training_readiness(root, config)
    if not report.ready:
        raise RuntimeError("training readiness failed: " + "; ".join(report.blockers))

    torch, load_dataset, LoraConfig, AutoTokenizer, trainers = _training_imports()
    _validate_hardware(torch, config)
    _validate_clean_git(root)

    output_dir = (root / config.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    status_path = output_dir / "run_status.json"
    manifest = _run_manifest(root, config, config_path, report.model_dump(mode="json"))
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_status(status_path, "running")

    try:
        data_manifest = json.loads(
            (root / config.data.manifest_path).read_text(encoding="utf-8")
        )
        train_path = root / data_manifest["files"][config.data.train_key]["path"]
        eval_path = root / data_manifest["files"][config.data.validation_key]["path"]
        train_dataset = load_dataset("json", data_files=str(train_path), split="train")
        eval_dataset = load_dataset("json", data_files=str(eval_path), split="train")
        tokenizer = AutoTokenizer.from_pretrained(
            config.model.model_id,
            revision=config.model.revision,
            trust_remote_code=config.model.trust_remote_code,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        common = dict(
            output_dir=str(output_dir),
            seed=config.seed,
            data_seed=config.seed,
            max_length=config.trainer.max_length,
            per_device_train_batch_size=config.trainer.per_device_train_batch_size,
            per_device_eval_batch_size=config.trainer.per_device_eval_batch_size,
            gradient_accumulation_steps=config.trainer.gradient_accumulation_steps,
            learning_rate=config.trainer.learning_rate,
            max_steps=config.trainer.max_steps,
            warmup_ratio=config.trainer.warmup_ratio,
            logging_steps=config.trainer.logging_steps,
            eval_strategy="steps",
            eval_steps=config.trainer.eval_steps,
            save_strategy="steps",
            save_steps=config.trainer.save_steps,
            save_total_limit=config.trainer.save_total_limit,
            gradient_checkpointing=config.trainer.gradient_checkpointing,
            bf16=config.trainer.bf16,
            tf32=config.trainer.tf32,
            report_to="none",
            push_to_hub=False,
            model_init_kwargs={
                "revision": config.model.revision,
                "dtype": torch.bfloat16,
                "trust_remote_code": config.model.trust_remote_code,
            },
        )
        if config.stage == "sft":
            SFTConfig, SFTTrainer = trainers["sft"]
            assert config.lora is not None
            args = SFTConfig(
                **common,
                packing=config.trainer.packing,
                completion_only_loss=config.trainer.completion_only_loss,
            )
            peft = LoraConfig(
                r=config.lora.rank,
                lora_alpha=config.lora.alpha,
                lora_dropout=config.lora.dropout,
                target_modules=config.lora.target_modules,
                bias=config.lora.bias,
                task_type="CAUSAL_LM",
            )
            trainer = SFTTrainer(
                model=config.model.model_id,
                args=args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                processing_class=tokenizer,
                peft_config=peft,
            )
        else:
            DPOConfig, DPOTrainer, AutoModelForCausalLM, PeftModel = trainers["dpo"]
            assert config.model.initial_adapter_path is not None
            base_model = AutoModelForCausalLM.from_pretrained(
                config.model.model_id,
                revision=config.model.revision,
                dtype=torch.bfloat16,
                trust_remote_code=config.model.trust_remote_code,
            )
            model = PeftModel.from_pretrained(
                base_model,
                str(root / config.model.initial_adapter_path),
                is_trainable=True,
            )
            dpo_common = {key: value for key, value in common.items() if key != "model_init_kwargs"}
            args = DPOConfig(
                **dpo_common,
                loss_type=config.trainer.loss_type,
                beta=config.trainer.beta,
            )
            trainer = DPOTrainer(
                model=model,
                ref_model=None,
                args=args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                processing_class=tokenizer,
            )

        trainer.train()
        trainer.save_model(str(output_dir / "adapter"))
        tokenizer.save_pretrained(str(output_dir / "adapter"))
        _write_status(status_path, "completed")
    except Exception:
        _write_status(status_path, "failed")
        raise
    return output_dir


def _training_imports():
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer
    except ImportError as exc:
        raise RuntimeError(
            "training stack is incomplete; install the pinned server dependency lock"
        ) from exc
    return (
        torch,
        load_dataset,
        LoraConfig,
        AutoTokenizer,
        {
            "sft": (SFTConfig, SFTTrainer),
            "dpo": (DPOConfig, DPOTrainer, AutoModelForCausalLM, PeftModel),
        },
    )


def _validate_hardware(torch: Any, config: TrainingRunConfig) -> None:
    if config.hardware.require_linux and platform.system() != "Linux":
        raise RuntimeError("this training config requires Linux")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    count = torch.cuda.device_count()
    if count < config.hardware.min_gpu_count:
        raise RuntimeError(
            f"requires {config.hardware.min_gpu_count} GPUs but only {count} are visible"
        )
    for index in range(config.hardware.min_gpu_count):
        memory_gib = torch.cuda.get_device_properties(index).total_memory / 1024**3
        if memory_gib < config.hardware.min_gpu_memory_gib:
            raise RuntimeError(
                f"GPU {index} has {memory_gib:.2f} GiB; "
                f"requires {config.hardware.min_gpu_memory_gib:.2f} GiB"
            )
    if config.hardware.require_bf16 and not torch.cuda.is_bf16_supported():
        raise RuntimeError("BF16 is required but unsupported")


def _validate_clean_git(root: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        check=True,
        text=True,
    )
    if completed.stdout.strip():
        raise RuntimeError("training requires a clean Git worktree")


def _run_manifest(
    root: Path,
    config: TrainingRunConfig,
    config_path: Path,
    readiness: dict[str, Any],
) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    packages = {}
    for name in ("torch", "transformers", "trl", "datasets", "peft", "accelerate"):
        packages[name] = importlib.metadata.version(name)
    return {
        "run_id": config.run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "config_path": config_path.resolve().relative_to(root.resolve()).as_posix(),
        "config": config.model_dump(mode="json"),
        "readiness": readiness,
        "packages": packages,
        "platform": platform.platform(),
    }


def _write_status(path: Path, status: str) -> None:
    path.write_text(
        json.dumps(
            {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
