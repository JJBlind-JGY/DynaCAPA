"""Strict, versioned configuration for TRL SFT and DPO runs."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from dynacapa.core.schemas import StrictModel


class ModelConfig(StrictModel):
    model_id: str = Field(min_length=1)
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    initial_adapter_path: str | None = None
    trust_remote_code: bool = False


class TrainingDataConfig(StrictModel):
    manifest_path: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    train_key: str = Field(min_length=1)
    validation_key: str = Field(min_length=1)


class LoRAConfig(StrictModel):
    rank: int = Field(gt=0)
    alpha: int = Field(gt=0)
    dropout: float = Field(ge=0.0, lt=1.0)
    target_modules: str = "all-linear"
    bias: Literal["none", "all", "lora_only"] = "none"


class TrainerConfig(StrictModel):
    max_length: int = Field(gt=0, le=4096)
    per_device_train_batch_size: int = Field(gt=0)
    per_device_eval_batch_size: int = Field(gt=0)
    gradient_accumulation_steps: int = Field(gt=0)
    learning_rate: float = Field(gt=0.0)
    max_steps: int = Field(gt=0)
    warmup_ratio: float = Field(ge=0.0, lt=1.0)
    logging_steps: int = Field(gt=0)
    eval_steps: int = Field(gt=0)
    save_steps: int = Field(gt=0)
    save_total_limit: int = Field(gt=0)
    gradient_checkpointing: bool = True
    bf16: bool = True
    tf32: bool = True
    packing: bool = False
    completion_only_loss: bool = True
    loss_type: (
        Literal["sigmoid"]
        | tuple[Literal["sigmoid", "sft"], ...]
        | None
    ) = None
    loss_weights: tuple[float, ...] | None = None
    beta: float | None = Field(default=None, gt=0.0)


class HardwareConfig(StrictModel):
    require_linux: bool = True
    min_gpu_count: int = Field(gt=0)
    min_gpu_memory_gib: float = Field(gt=0.0)
    require_bf16: bool = True


class TrainingRunConfig(StrictModel):
    config_version: Literal["1.0"] = "1.0"
    run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    stage: Literal["sft", "dpo"]
    purpose: Literal["pipeline_smoke", "formal"]
    enabled: bool
    seed: int
    output_dir: str = Field(min_length=1)
    model: ModelConfig
    data: TrainingDataConfig
    lora: LoRAConfig | None
    trainer: TrainerConfig
    hardware: HardwareConfig
    expected_dependency_lock: str = Field(min_length=1)

    @model_validator(mode="after")
    def stage_contract(self) -> TrainingRunConfig:
        if self.stage == "sft":
            if self.model.initial_adapter_path is not None:
                raise ValueError("SFT must start from the pinned base model")
            if self.lora is None:
                raise ValueError("SFT requires an explicit LoRA configuration")
            if (
                self.trainer.loss_type is not None
                or self.trainer.loss_weights is not None
                or self.trainer.beta is not None
            ):
                raise ValueError("SFT cannot define DPO loss_type, loss_weights, or beta")
            if not self.data.train_key.endswith("_sft"):
                raise ValueError("SFT train_key must select an SFT artifact")
        else:
            if self.model.initial_adapter_path is None:
                raise ValueError("DPO must name the preceding SFT adapter path")
            if self.lora is not None:
                raise ValueError("DPO continues the SFT adapter; do not create a second LoRA")
            loss_types = (
                (self.trainer.loss_type,)
                if isinstance(self.trainer.loss_type, str)
                else self.trainer.loss_type
            )
            if not loss_types or "sigmoid" not in loss_types or self.trainer.beta is None:
                raise ValueError("DPO must explicitly include sigmoid loss and beta")
            if len(loss_types) != len(set(loss_types)):
                raise ValueError("DPO loss_type entries must be unique")
            if self.trainer.loss_weights is not None and len(
                self.trainer.loss_weights
            ) != len(loss_types):
                raise ValueError("DPO loss_weights must align with loss_type")
            if "sft" in loss_types and self.trainer.loss_weights is None:
                raise ValueError("mixed sigmoid+sft DPO requires explicit loss_weights")
            if not self.data.train_key.endswith("_dpo"):
                raise ValueError("DPO train_key must select a DPO artifact")
        if self.stage not in self.data.validation_key:
            raise ValueError("validation_key must match the training stage")
        return self
