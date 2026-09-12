"""Rights and facts are updated together but never conflated."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from dynacapa.core.enums import IssuerType
from dynacapa.core.schemas import AuthorizationEvent, Fact, StrictModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthorizationState(StrictModel):
    version: int = Field(ge=0)
    events: tuple[AuthorizationEvent, ...]
    facts: tuple[Fact, ...]

    def event_by_id(self, event_id: str) -> AuthorizationEvent | None:
        return next((event for event in self.events if event.id == event_id), None)

    def fact_by_id(self, fact_id: str) -> Fact | None:
        return next((fact for fact in self.facts if fact.id == fact_id), None)

    def freshest_fact(self, key: str, at: datetime) -> Fact | None:
        candidates = [fact for fact in self.facts if fact.key == key and fact.is_fresh(at)]
        return max(candidates, key=lambda fact: fact.observed_at, default=None)

    def conditions_hold(self, event: AuthorizationEvent, at: datetime) -> bool:
        for key, required_value in event.conditions.items():
            fact = self.freshest_fact(key, at)
            if fact is None or fact.value != required_value:
                return False
        return True

    def active_rights(self, at: datetime | None = None) -> tuple[AuthorizationEvent, ...]:
        selected_at = at or _utc_now()
        trusted_issuers = {IssuerType.AUTHENTICATED_USER, IssuerType.TRUSTED_SYSTEM}
        return tuple(
            event
            for event in self.events
            if event.issuer_type in trusted_issuers
            and not event.revoked
            and event.is_time_valid(selected_at)
            and self.conditions_hold(event, selected_at)
        )

    def authorizations_for(
        self,
        action_type: str,
        object_scope: tuple[str, ...],
        target_scope: tuple[str, ...],
        at: datetime | None = None,
    ) -> tuple[AuthorizationEvent, ...]:
        return tuple(
            event
            for event in self.active_rights(at)
            if event.action_type == action_type
            and _scope_covers(event.object_scope, object_scope)
            and _scope_covers(event.target_scope, target_scope)
        )


def _scope_covers(allowed: tuple[str, ...], requested: tuple[str, ...]) -> bool:
    if not requested:
        return True
    return "*" in allowed or set(requested).issubset(allowed)


class AuthorizationEngine:
    def __init__(self) -> None:
        self._events: dict[str, AuthorizationEvent] = {}
        self._facts: dict[str, Fact] = {}
        self._version = 0

    def update(
        self,
        events: tuple[AuthorizationEvent, ...] | list[AuthorizationEvent] = (),
        facts: tuple[Fact, ...] | list[Fact] = (),
    ) -> AuthorizationState:
        changed = False
        for event in events:
            current = self._events.get(event.id)
            if current is not None and event.version < current.version:
                raise ValueError(f"stale authorization update: {event.id}")
            if current != event:
                self._events[event.id] = event.model_copy(deep=True)
                changed = True
        for fact in facts:
            if self._facts.get(fact.id) != fact:
                self._facts[fact.id] = fact.model_copy(deep=True)
                changed = True
        if changed:
            self._version += 1
        return self.state()

    def state(self) -> AuthorizationState:
        return AuthorizationState(
            version=self._version,
            events=tuple(
                item.model_copy(deep=True)
                for item in sorted(self._events.values(), key=lambda item: item.id)
            ),
            facts=tuple(
                item.model_copy(deep=True)
                for item in sorted(self._facts.values(), key=lambda item: item.id)
            ),
        )
