"""Versioned, immutable schemas shared by every research stage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)

from dynacapa.core.constants import SCHEMA_VERSION
from dynacapa.core.enums import (
    IssuerType,
    PolicyMode,
    ReasonCode,
    SideEffectLevel,
    SourceType,
    Termination,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class VersionedModel(StrictModel):
    schema_version: str = SCHEMA_VERSION


class AuthorizationEvent(VersionedModel):
    id: str = Field(min_length=1)
    issuer_type: IssuerType
    action_type: str = Field(min_length=1)
    object_scope: tuple[str, ...] = ()
    target_scope: tuple[str, ...] = ()
    conditions: dict[str, JsonValue] = Field(default_factory=dict)
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    confirmation_required: bool = False
    revoked: bool = False
    source_ref: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)

    @field_validator("object_scope", "target_scope")
    @classmethod
    def unique_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("scope entries must be unique")
        return value

    @model_validator(mode="after")
    def valid_interval(self) -> AuthorizationEvent:
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        return self

    def is_time_valid(self, at: datetime) -> bool:
        return (self.valid_from is None or at >= self.valid_from) and (
            self.valid_until is None or at < self.valid_until
        )


class Fact(VersionedModel):
    id: str = Field(min_length=1)
    key: str = Field(min_length=1)
    value: JsonValue
    source_type: SourceType
    source_id: str = Field(min_length=1)
    observed_at: AwareDatetime
    ttl_seconds: int | None = Field(default=None, gt=0)

    def is_fresh(self, at: datetime) -> bool:
        if at < self.observed_at:
            return False
        if self.ttl_seconds is None:
            return True
        return (at - self.observed_at).total_seconds() <= self.ttl_seconds


class CriticalArgRule(StrictModel):
    allowed_source_types: tuple[SourceType, ...]
    required: bool = True


class DynamicToolContract(VersionedModel):
    tool_name: str = Field(min_length=1)
    tool_schema_version: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    authorization_version: int = Field(ge=0)
    action_type: str = Field(min_length=1)
    allowed_modes: tuple[PolicyMode, ...]
    critical_args: dict[str, CriticalArgRule] = Field(default_factory=dict)
    allowed_object_scope: tuple[str, ...] = ()
    allowed_target_scope: tuple[str, ...] = ()
    confirmation_required: bool = False
    reversible: bool
    preview_supported: bool
    side_effect_level: SideEffectLevel


class ProofCertificate(VersionedModel):
    action_type: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    authorization_refs: tuple[str, ...]
    source_refs: dict[str, str] = Field(default_factory=dict)
    object_scope: tuple[str, ...] = ()
    target_scope: tuple[str, ...] = ()
    confirmation_refs: tuple[str, ...] = ()
    tool_schema_version: str = Field(min_length=1)
    expected_effects: dict[str, JsonValue] = Field(default_factory=dict)
    rollback_plan: str | None = None


class ActionPolicyOutput(VersionedModel):
    mode: Literal[PolicyMode.EXECUTE, PolicyMode.SANDBOX, PolicyMode.REWRITE]
    termination: Literal[Termination.CONTINUE, Termination.SUCCESS] = Termination.CONTINUE
    tool: str = Field(min_length=1)
    args: dict[str, JsonValue]
    proof: ProofCertificate


class AskPolicyOutput(VersionedModel):
    mode: Literal[PolicyMode.ASK]
    termination: Literal[Termination.CONTINUE] = Termination.CONTINUE
    question: str = Field(min_length=1)
    missing_fields: tuple[str, ...]


class BlockPolicyOutput(VersionedModel):
    mode: Literal[PolicyMode.BLOCK]
    termination: Literal[Termination.CONTINUE, Termination.SAFE_STOP] = Termination.CONTINUE
    reason_code: ReasonCode
    detail: str = Field(min_length=1)


class StopPolicyOutput(VersionedModel):
    mode: Literal[PolicyMode.STOP]
    termination: Literal[Termination.SAFE_STOP] = Termination.SAFE_STOP
    reason_code: ReasonCode
    detail: str = Field(min_length=1)


PolicyOutput = Annotated[
    ActionPolicyOutput | AskPolicyOutput | BlockPolicyOutput | StopPolicyOutput,
    Field(discriminator="mode"),
]
POLICY_OUTPUT_ADAPTER = TypeAdapter(PolicyOutput)


class VerifierChecks(StrictModel):
    bind_ok: bool = False
    auth_path_ok: bool = False
    param_source_ok: bool = False
    scope_ok: bool = False
    confirm_ok: bool = False
    effect_ok: bool = False
    rollback_ok: bool = False
    freshness_ok: bool = False
    revocation_ok: bool = False
    schema_version_ok: bool = False

    @classmethod
    def all_passed(cls) -> VerifierChecks:
        return cls(**{name: True for name in cls.model_fields})


class InterventionCandidate(StrictModel):
    mode: PolicyMode
    reason: ReasonCode
    target_fields: tuple[str, ...]


class VerifierResult(VersionedModel):
    hard_violation: bool
    checks: VerifierChecks
    reason_codes: tuple[ReasonCode, ...] = ()
    soft_costs: dict[str, float] = Field(default_factory=dict)
    intervention_candidates: tuple[InterventionCandidate, ...] = ()


class StateSnapshot(VersionedModel):
    id: str = Field(min_length=1)
    env_type: str = Field(min_length=1)
    env_version: str = Field(min_length=1)
    authorization_version: int = Field(default=0, ge=0)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    seed: int
    rng_state: JsonValue
    payload: dict[str, JsonValue]
    environment_state_hash: str = Field(min_length=64, max_length=64)
    state_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=utc_now)


class EnvironmentStep(VersionedModel):
    observation: dict[str, JsonValue]
    state_hash: str = Field(min_length=64, max_length=64)
    task_reward: float = 0.0
    soft_costs: dict[str, float] = Field(default_factory=dict)
    terminal: bool = False


class Transition(VersionedModel):
    state_id: str = Field(min_length=1)
    candidate_output: PolicyOutput
    verifier_result: VerifierResult
    executed_output: PolicyOutput
    shield_intervened: bool
    shield_edit_fields: tuple[str, ...] = ()
    task_reward: float
    soft_costs: dict[str, float]
    observation: dict[str, JsonValue]
    next_state_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)


class ReplayPair(VersionedModel):
    id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    seed: int
    target_field: str = Field(min_length=1)
    original_transition: Transition
    intervened_transition: Transition
    return_delta: float
    cost_deltas: dict[str, float]
    environment_calls: int = Field(ge=0)
    token_count: int = Field(ge=0)
    optimizer_steps: int = Field(ge=0)


class TrajectoryFinal(StrictModel):
    trusted_success: bool
    system_success: bool
    attack_success: bool
    unauthorized_proposal: bool
    unauthorized_execution: bool
    shield_interventions: int = Field(ge=0)


class Trajectory(VersionedModel):
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    config_id: str = Field(min_length=1)
    git_commit: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    dataset_hash: str = Field(min_length=1)
    seed: int
    env_version: str = Field(min_length=1)
    verifier_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    steps: tuple[Transition, ...]
    final: TrajectoryFinal
