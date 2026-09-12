"""Compile current authorization state into an executable tool contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from pydantic import Field

from dynacapa.authorization.engine import AuthorizationState
from dynacapa.core.enums import PolicyMode, SideEffectLevel
from dynacapa.core.schemas import CriticalArgRule, DynamicToolContract, StrictModel


class ToolDefinition(StrictModel):
    tool_name: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    allowed_modes: tuple[PolicyMode, ...] = (
        PolicyMode.EXECUTE,
        PolicyMode.SANDBOX,
        PolicyMode.REWRITE,
    )
    critical_args: dict[str, CriticalArgRule] = Field(default_factory=dict)
    reversible: bool
    preview_supported: bool
    side_effect_level: SideEffectLevel
    confirmation_required: bool = False


def default_mail_tool_definitions() -> dict[str, ToolDefinition]:
    from dynacapa.core.enums import SourceType

    recipient_rule = CriticalArgRule(
        allowed_source_types=(
            SourceType.AUTHENTICATED_USER,
            SourceType.TRUSTED_SYSTEM,
            SourceType.TRUSTED_CONTACT_DB,
        )
    )
    return {
        "create_draft": ToolDefinition(
            tool_name="create_draft",
            schema_version="v1",
            action_type="create_draft",
            critical_args={"recipient": recipient_rule},
            reversible=True,
            preview_supported=True,
            side_effect_level=SideEffectLevel.LOW,
        ),
        "send_email": ToolDefinition(
            tool_name="send_email",
            schema_version="v1",
            action_type="send_email",
            critical_args={"recipient": recipient_rule},
            reversible=False,
            preview_supported=True,
            side_effect_level=SideEffectLevel.HIGH,
        ),
    }


class DynamicContractCompiler:
    def compile(
        self,
        auth_state: AuthorizationState,
        env_state: dict[str, object],
        tool_schema: ToolDefinition,
        at: datetime | None = None,
    ) -> DynamicToolContract:
        del env_state  # Reserved for state-dependent contracts in the next milestone.
        selected_at = at or datetime.now(timezone.utc)
        rights = tuple(
            right
            for right in auth_state.active_rights(selected_at)
            if right.action_type == tool_schema.action_type
        )
        object_scope = _stable_union(right.object_scope for right in rights)
        target_scope = _stable_union(right.target_scope for right in rights)
        confirmation_required = tool_schema.confirmation_required or any(
            right.confirmation_required for right in rights
        )
        digest_input = {
            "authorization_version": auth_state.version,
            "tool": tool_schema.model_dump(mode="json"),
            "object_scope": object_scope,
            "target_scope": target_scope,
            "confirmation_required": confirmation_required,
        }
        digest = hashlib.sha256(
            json.dumps(digest_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        return DynamicToolContract(
            tool_name=tool_schema.tool_name,
            tool_schema_version=tool_schema.schema_version,
            contract_version=f"dc-{digest}",
            authorization_version=auth_state.version,
            action_type=tool_schema.action_type,
            allowed_modes=tool_schema.allowed_modes,
            critical_args=tool_schema.critical_args,
            allowed_object_scope=object_scope,
            allowed_target_scope=target_scope,
            confirmation_required=confirmation_required,
            reversible=tool_schema.reversible,
            preview_supported=tool_schema.preview_supported,
            side_effect_level=tool_schema.side_effect_level,
        )


def _stable_union(scopes: object) -> tuple[str, ...]:
    values: set[str] = set()
    for scope in scopes:
        values.update(scope)
    return tuple(sorted(values))

