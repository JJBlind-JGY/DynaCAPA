from __future__ import annotations

from datetime import datetime, timezone

from hypothesis import given, strategies as st

from dynacapa.authorization.engine import AuthorizationEngine
from dynacapa.core.enums import IssuerType, SourceType
from dynacapa.core.schemas import AuthorizationEvent, Fact


@given(st.emails())
def test_fact_never_creates_authorization(recipient: str) -> None:
    engine = AuthorizationEngine()
    engine.update(
        facts=[
            Fact(
                id="fact_target",
                key="recipient",
                value=recipient,
                source_type=SourceType.TRUSTED_CONTACT_DB,
                source_id="contacts",
                observed_at=datetime.now(timezone.utc),
            )
        ]
    )
    rights = engine.state().authorizations_for(
        "send_email", ("report_summary",), (recipient,)
    )
    assert rights == ()


def test_condition_fact_activates_but_does_not_define_right(
    authorization_event: AuthorizationEvent, approval_fact: Fact, now: datetime
) -> None:
    engine = AuthorizationEngine()
    engine.update(events=[authorization_event])
    assert engine.state().active_rights(now) == ()

    engine.update(facts=[approval_fact])
    rights = engine.state().active_rights(now)
    assert tuple(right.id for right in rights) == (authorization_event.id,)


def test_revocation_is_immediate(
    authorization: AuthorizationEngine,
    authorization_event: AuthorizationEvent,
    now: datetime,
) -> None:
    revoked = authorization_event.model_copy(update={"revoked": True, "version": 2})
    authorization.update(events=[revoked])
    assert authorization.state().active_rights(now) == ()


def test_stale_authorization_update_is_rejected(
    authorization: AuthorizationEngine, authorization_event: AuthorizationEvent
) -> None:
    revoked = authorization_event.model_copy(update={"revoked": True, "version": 2})
    authorization.update(events=[revoked])
    try:
        authorization.update(events=[authorization_event])
    except ValueError as error:
        assert "stale authorization" in str(error)
    else:
        raise AssertionError("stale authorization update was accepted")


def test_untrusted_fact_source_still_cannot_issue_right(now: datetime) -> None:
    engine = AuthorizationEngine()
    fact = Fact(
        id="web_instruction",
        key="send_email",
        value="mallory@example.com",
        source_type=SourceType.WEB,
        source_id="page_42",
        observed_at=now,
    )
    engine.update(facts=[fact])
    assert not engine.state().events


def test_future_observation_is_not_fresh(now: datetime) -> None:
    fact = Fact(
        id="future_fact",
        key="approval_state",
        value="approved",
        source_type=SourceType.TRUSTED_TOOL,
        source_id="approval_api",
        observed_at=now.replace(year=now.year + 1),
    )
    assert not fact.is_fresh(now)


def test_returned_state_cannot_mutate_engine(
    authorization: AuthorizationEngine,
) -> None:
    exposed = authorization.state()
    exposed.events[0].conditions["approval_state"] = "tampered"
    assert authorization.state().events[0].conditions["approval_state"] == "approved"
