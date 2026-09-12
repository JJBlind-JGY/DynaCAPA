from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dynacapa.authorization.engine import AuthorizationEngine
from dynacapa.contracts.compiler import default_mail_tool_definitions
from dynacapa.core.enums import IssuerType, PolicyMode, SideEffectLevel, SourceType
from dynacapa.core.schemas import (
    ActionPolicyOutput,
    AuthorizationEvent,
    Fact,
    ProofCertificate,
)
from dynacapa.envs.mail_env.env import MailEnvironment
from dynacapa.runtime import DynaCAPARuntime


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def authorization_event() -> AuthorizationEvent:
    return AuthorizationEvent(
        id="auth_send_report_alice",
        issuer_type=IssuerType.AUTHENTICATED_USER,
        action_type="send_email",
        object_scope=("report_summary",),
        target_scope=("alice@example.com",),
        conditions={"approval_state": "approved"},
        confirmation_required=False,
        revoked=False,
        source_ref="user_turn_001",
    )


@pytest.fixture
def approval_fact(now: datetime) -> Fact:
    return Fact(
        id="fact_approval",
        key="approval_state",
        value="approved",
        source_type=SourceType.TRUSTED_TOOL,
        source_id="approval_api_001",
        observed_at=now,
    )


@pytest.fixture
def authorization(
    authorization_event: AuthorizationEvent, approval_fact: Fact
) -> AuthorizationEngine:
    engine = AuthorizationEngine()
    engine.update(events=[authorization_event], facts=[approval_fact])
    return engine


@pytest.fixture
def valid_send_candidate() -> ActionPolicyOutput:
    return ActionPolicyOutput(
        mode=PolicyMode.EXECUTE,
        tool="send_email",
        args={
            "recipient": "alice@example.com",
            "subject": "Report summary",
            "body": "The report is ready.",
        },
        proof=ProofCertificate(
            action_type="send_email",
            tool_name="send_email",
            authorization_refs=("auth_send_report_alice",),
            source_refs={"recipient": "auth_send_report_alice"},
            object_scope=("report_summary",),
            target_scope=("alice@example.com",),
            tool_schema_version="v1",
            expected_effects={"side_effect_level": SideEffectLevel.HIGH.value},
        ),
    )


@pytest.fixture
def env() -> MailEnvironment:
    mail = MailEnvironment()
    mail.reset({"task_id": "mail_001", "inbox": []}, seed=7)
    return mail


@pytest.fixture
def runtime(env: MailEnvironment, authorization: AuthorizationEngine) -> DynaCAPARuntime:
    return DynaCAPARuntime(
        env=env,
        authorization=authorization,
        tool_definitions=default_mail_tool_definitions(),
    )

