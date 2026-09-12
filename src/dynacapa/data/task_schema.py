"""Structured ground truth for generated Mail tasks."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from dynacapa.core.enums import PolicyMode, ReasonCode, SourceType
from dynacapa.core.schemas import AuthorizationEvent, Fact, StrictModel, VersionedModel


class ContextMessage(StrictModel):
    id: str = Field(min_length=1)
    source_type: SourceType
    source_id: str = Field(min_length=1)
    content: str


class GroundTruthAction(StrictModel):
    mode: PolicyMode
    tool: str = Field(min_length=1)
    args: dict[str, str]
    reason_code: ReasonCode | None = None


class TaskGroundTruth(StrictModel):
    user_goal: str = Field(min_length=1)
    authorization_events: tuple[AuthorizationEvent, ...]
    initial_facts: tuple[Fact, ...]
    hidden_facts: tuple[Fact, ...]
    legal_actions: tuple[GroundTruthAction, ...]
    illegal_actions: tuple[GroundTruthAction, ...]
    expected_side_effects: tuple[str, ...]
    acceptable_modes: tuple[PolicyMode, ...]
    required_confirmations: tuple[str, ...]


class TaskScenario(StrictModel):
    attack_type: str = Field(min_length=1)
    attack_expression_id: str = Field(min_length=1)
    authorization_pattern: str = Field(min_length=1)
    tool_schema_version: str = Field(min_length=1)
    source_combination: str = Field(min_length=1)
    source_conflict: bool
    horizon: int = Field(ge=1)


class TaskProvenance(StrictModel):
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    generator_seed: int
    template_id: str = Field(min_length=1)
    record_fingerprint: str = Field(min_length=64, max_length=64)


class MailTaskRecord(VersionedModel):
    task_id: str = Field(min_length=1)
    split: str = Field(pattern=r"^(train|validation|frozen_test)$")
    diagnostic_group: str = Field(min_length=1)
    natural_language_request: str = Field(min_length=1)
    evaluation_time: AwareDatetime
    context_messages: tuple[ContextMessage, ...]
    ground_truth: TaskGroundTruth
    scenario: TaskScenario
    provenance: TaskProvenance

