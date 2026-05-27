import pytest

from app.models import (
    Action,
    ActionType,
    Comparator,
    Comparison,
    FieldSpec,
    FieldType,
    InputSchema,
    Rule,
    RuleSet,
)
from app.validation import ValidationError, detect_cycle, validate_rule_set


def schema():
    return InputSchema(
        fields=[
            FieldSpec(name="amount", type=FieldType.NUMBER),
            FieldSpec(name="country", type=FieldType.STRING),
            FieldSpec(name="tier", type=FieldType.STRING),
        ]
    )


def flag(target):
    return Action(type=ActionType.FLAG, target=target, value=True)


def test_valid_rule_set_passes():
    rs = RuleSet(
        name="ok",
        input_schema=schema(),
        rules=[
            Rule(
                id="big",
                condition=Comparison(field="amount", op=Comparator.GTE, value=1000),
                actions=[flag("review")],
            )
        ],
    )
    validate_rule_set(rs)


def test_unknown_field_is_rejected():
    rs = RuleSet(
        name="bad",
        input_schema=schema(),
        rules=[
            Rule(
                id="r",
                condition=Comparison(field="nope", op=Comparator.EQ, value=1),
                actions=[flag("x")],
            )
        ],
    )
    with pytest.raises(ValidationError, match="unknown field 'nope'"):
        validate_rule_set(rs)


def test_numeric_operator_on_string_field_is_rejected():
    rs = RuleSet(
        name="bad",
        input_schema=schema(),
        rules=[
            Rule(
                id="r",
                condition=Comparison(field="country", op=Comparator.GT, value=5),
                actions=[flag("x")],
            )
        ],
    )
    with pytest.raises(ValidationError, match="numeric operator"):
        validate_rule_set(rs)


def test_rule_without_actions_is_rejected():
    rs = RuleSet(
        name="bad",
        input_schema=schema(),
        rules=[
            Rule(
                id="r",
                condition=Comparison(field="amount", op=Comparator.GT, value=1),
                actions=[],
            )
        ],
    )
    with pytest.raises(ValidationError, match="no actions"):
        validate_rule_set(rs)


def test_in_operator_needs_a_list():
    rs = RuleSet(
        name="bad",
        input_schema=schema(),
        rules=[
            Rule(
                id="r",
                condition=Comparison(field="country", op=Comparator.IN, value="US"),
                actions=[flag("x")],
            )
        ],
    )
    with pytest.raises(ValidationError, match="needs a list"):
        validate_rule_set(rs)


def chain_rule(rule_id, reads_field, writes_field):
    return Rule(
        id=rule_id,
        condition=Comparison(field=reads_field, op=Comparator.EQ, value="yes"),
        actions=[Action(type=ActionType.SET, target=writes_field, value="yes")],
        triggers=[writes_field],
    )


def test_acyclic_chain_has_no_cycle():
    rules = [
        chain_rule("a", "country", "tier"),
        chain_rule("b", "tier", "amount"),
    ]
    assert detect_cycle(rules) is None


def test_cyclic_chain_is_detected():
    # a writes tier which b reads, b writes country which a reads: a loop.
    rules = [
        chain_rule("a", "country", "tier"),
        chain_rule("b", "tier", "country"),
    ]
    cycle = detect_cycle(rules)
    assert cycle is not None
    assert "a" in cycle and "b" in cycle


def test_validate_rejects_cyclic_rule_set():
    rs = RuleSet(
        name="loopy",
        input_schema=schema(),
        rules=[
            chain_rule("a", "country", "tier"),
            chain_rule("b", "tier", "country"),
        ],
    )
    with pytest.raises(ValidationError, match="cyclic rule chain"):
        validate_rule_set(rs)
