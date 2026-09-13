from __future__ import annotations

import json
from pathlib import Path

import yaml

from dynacapa.core.enums import PolicyMode
from dynacapa.core.schemas import POLICY_OUTPUT_ADAPTER
from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.data.training import FORBIDDEN_PROMPT_KEYS, compile_training_examples


ROOT = Path(__file__).resolve().parents[2]


def _records():
    raw = yaml.safe_load((ROOT / "configs/data/mail_v0_2.yaml").read_text("utf-8"))
    config = MailDatasetConfig.model_validate({**raw, "train_count": 120})
    return generate_mail_dataset(config)["train"]


def test_compiler_is_deterministic_and_aligned() -> None:
    records = _records()
    first = compile_training_examples(records)
    second = compile_training_examples(tuple(reversed(records)))

    assert first == second
    assert len(first.sft) == len(records)
    assert len(first.dpo) == len(records)
    assert {item.task_id for item in first.sft} == {item.task_id for item in first.dpo}
    assert first.audit["one_to_one_task_alignment"] is True
    assert first.audit["frozen_test_accessed"] is False


def test_prompts_exclude_oracle_fields_and_outputs_parse() -> None:
    compilation = compile_training_examples(_records())
    for example in compilation.sft:
        prompt = "\n".join(message.content for message in example.prompt)
        assert all(f'"{key}"' not in prompt for key in FORBIDDEN_PROMPT_KEYS)
        parsed = POLICY_OUTPUT_ADAPTER.validate_json(example.completion[0].content)
        assert parsed.mode == example.target_mode
    for example in compilation.dpo:
        chosen = POLICY_OUTPUT_ADAPTER.validate_json(example.chosen[0].content)
        rejected = POLICY_OUTPUT_ADAPTER.validate_json(example.rejected[0].content)
        assert chosen.mode == example.chosen_mode
        assert rejected.mode == PolicyMode.EXECUTE
        assert example.chosen[0].content != example.rejected[0].content
        assert example.rejection_reasons


def test_compiler_rejects_frozen_test() -> None:
    raw = yaml.safe_load((ROOT / "configs/data/mail_v0_2.yaml").read_text("utf-8"))
    config = MailDatasetConfig.model_validate({**raw, "frozen_test_count": 12})
    frozen = generate_mail_dataset(config)["frozen_test"]

    try:
        compile_training_examples(frozen)
    except ValueError as exc:
        assert "frozen_test" in str(exc)
    else:
        raise AssertionError("frozen_test compilation should fail closed")


def test_prompt_state_sections_are_explicitly_separated() -> None:
    example = compile_training_examples(_records()).sft[0]
    payload = json.loads(example.prompt[1].content)
    assert set(payload) >= {
        "authorization_rights",
        "facts",
        "executable_set",
        "tool_contracts",
    }
    assert "mallory@example.net" not in json.dumps(
        payload["executable_set"], sort_keys=True
    )
