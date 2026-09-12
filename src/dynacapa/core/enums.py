"""Closed vocabularies for the public experiment protocol."""

from enum import StrEnum


class IssuerType(StrEnum):
    AUTHENTICATED_USER = "authenticated_user"
    TRUSTED_SYSTEM = "trusted_system"


class SourceType(StrEnum):
    AUTHENTICATED_USER = "authenticated_user"
    TRUSTED_SYSTEM = "trusted_system"
    TRUSTED_TOOL = "trusted_tool"
    TRUSTED_CONTACT_DB = "trusted_contact_db"
    UNTRUSTED_TOOL = "untrusted_tool"
    WEB = "web"
    DOCUMENT = "document"
    MEMORY = "memory"


class PolicyMode(StrEnum):
    EXECUTE = "execute"
    ASK = "ask"
    SANDBOX = "sandbox"
    REWRITE = "rewrite"
    BLOCK = "block"
    STOP = "stop"


class Termination(StrEnum):
    CONTINUE = "continue"
    SUCCESS = "success"
    SAFE_STOP = "safe_stop"


class SideEffectLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    IRREVERSIBLE = "irreversible"


class ReasonCode(StrEnum):
    TOOL_NOT_FOUND = "tool_not_found"
    MODE_NOT_ALLOWED = "mode_not_allowed"
    BINDING_MISMATCH = "binding_mismatch"
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_REVOKED = "authorization_revoked"
    CONDITION_UNSATISFIED = "condition_unsatisfied"
    PARAM_SOURCE_MISSING = "param_source_missing"
    PARAM_SOURCE_NOT_ALLOWED = "param_source_not_allowed"
    SCOPE_EXCEEDED = "scope_exceeded"
    CONFIRMATION_REQUIRED = "confirmation_required"
    EFFECT_MISMATCH = "effect_mismatch"
    ROLLBACK_MISSING = "rollback_missing"
    FACT_STALE = "fact_stale"
    SCHEMA_VERSION_MISMATCH = "schema_version_mismatch"
    SHIELD_BLOCKED = "shield_blocked"

