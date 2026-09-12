from __future__ import annotations

import pytest
from pydantic import ValidationError

from dynacapa.core.enums import PolicyMode, ReasonCode
from dynacapa.core.schemas import POLICY_OUTPUT_ADAPTER, BlockPolicyOutput


def test_policy_output_discriminator_rejects_tool_fields_on_block() -> None:
    with pytest.raises(ValidationError):
        POLICY_OUTPUT_ADAPTER.validate_python(
            {
                "mode": "block",
                "termination": "continue",
                "reason_code": "scope_exceeded",
                "detail": "unsafe",
                "tool": "send_email",
                "args": {},
            }
        )


def test_block_output_is_a_legal_union_member() -> None:
    output = POLICY_OUTPUT_ADAPTER.validate_python(
        {
            "mode": "block",
            "reason_code": "scope_exceeded",
            "detail": "recipient outside scope",
        }
    )
    assert isinstance(output, BlockPolicyOutput)
    assert output.mode == PolicyMode.BLOCK
    assert output.reason_code == ReasonCode.SCOPE_EXCEEDED

