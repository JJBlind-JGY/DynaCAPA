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


def test_contrastive_v2_balances_modes_without_duplication() -> None:
    records = _records()
    compilation = compile_training_examples(
        records,
        target_policy="minimum_intervention_contrastive_v2",
        balance_modes=True,
        selection_seed=20260913,
    )

    counts = compilation.audit["target_mode_distribution"]
    assert set(counts) == {"ask", "block", "execute"}
    assert len(set(counts.values())) == 1
    assert len(compilation.dpo) == 2 * len(compilation.sft)
    assert len({example.task_id for example in compilation.sft}) == len(compilation.sft)
    assert compilation.audit["complete_task_alignment"] is True
    assert compilation.audit["mode_balanced_by_downsampling"] is True


def test_contrastive_v2_has_hard_and_mode_disambiguation_pairs() -> None:
    compilation = compile_training_examples(
        _records(), target_policy="minimum_intervention_contrastive_v2"
    )
    pairs_by_task: dict[str, list] = {}
    for example in compilation.dpo:
        pairs_by_task.setdefault(example.task_id, []).append(example)
    assert all(len(examples) == 2 for examples in pairs_by_task.values())
    assert all(
        {example.rejection_basis for example in examples}
        == {"verifier_hard_violation", "policy_suboptimality"}
        for examples in pairs_by_task.values()
    )
    assert {
        example.pair_family for example in compilation.dpo
    } >= {
        "safe_execution_over_unnecessary_block",
        "confirmation_over_unnecessary_block",
        "block_over_unresolvable_ask",
    }
    assert all(
        example.rejection_reasons
        for example in compilation.dpo
        if example.rejection_basis == "verifier_hard_violation"
    )
    assert all(
        not example.rejection_reasons
        for example in compilation.dpo
        if example.rejection_basis == "policy_suboptimality"
    )
