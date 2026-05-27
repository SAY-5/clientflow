"""Property based tests for the evaluator.

These check invariants that must hold for any input and any rule set:
matching rules fire their actions, evaluation is deterministic, AND/OR
semantics are correct, and no input can crash the evaluator.
"""

from hypothesis import given
from hypothesis import strategies as st

from app.evaluator import evaluate, evaluate_condition
from app.models import (
    Action,
    ActionType,
    Comparator,
    Comparison,
    FieldSpec,
    FieldType,
    Group,
    InputSchema,
    Rule,
    RuleSet,
)

# Payloads with a small set of typed fields.
payloads = st.fixed_dictionaries(
    {
        "amount": st.integers(min_value=-10_000, max_value=10_000),
        "country": st.sampled_from(["US", "CA", "FR", "DE"]),
    }
)

scalars = st.one_of(
    st.integers(min_value=-10_000, max_value=10_000),
    st.text(max_size=8),
    st.booleans(),
    st.none(),
    st.lists(st.integers(), max_size=5),
)


def comparison_strategy():
    return st.builds(
        Comparison,
        field=st.sampled_from(["amount", "country", "missing"]),
        op=st.sampled_from(list(Comparator)),
        value=scalars,
    )


@given(payload=payloads, cmp=comparison_strategy())
def test_evaluator_never_crashes(payload, cmp):
    result = evaluate_condition(cmp, payload)
    assert result in (True, False)


@given(payload=payloads, cmp=comparison_strategy())
def test_evaluation_is_deterministic(payload, cmp):
    assert evaluate_condition(cmp, payload) == evaluate_condition(cmp, payload)


@given(payload=payloads, a=comparison_strategy(), b=comparison_strategy())
def test_and_matches_only_when_both_match(payload, a, b):
    group = Group(op="and", nodes=[a, b])
    expected = evaluate_condition(a, payload) and evaluate_condition(b, payload)
    assert evaluate_condition(group, payload) is expected


@given(payload=payloads, a=comparison_strategy(), b=comparison_strategy())
def test_or_matches_when_either_matches(payload, a, b):
    group = Group(op="or", nodes=[a, b])
    expected = evaluate_condition(a, payload) or evaluate_condition(b, payload)
    assert evaluate_condition(group, payload) is expected


@given(payload=payloads, threshold=st.integers(min_value=-10_000, max_value=10_000))
def test_matching_rule_always_fires_its_action(payload, threshold):
    rule = Rule(
        id="r",
        condition=Comparison(field="amount", op=Comparator.GTE, value=threshold),
        actions=[Action(type=ActionType.FLAG, target="hit", value=True)],
    )
    rs = RuleSet(
        name="t",
        input_schema=InputSchema(
            fields=[FieldSpec(name="amount", type=FieldType.NUMBER)]
        ),
        rules=[rule],
    )
    out = evaluate(rs, payload)
    if payload["amount"] >= threshold:
        assert out["fired"] == ["r"]
        assert out["result"]["hit"] is True
    else:
        assert out["fired"] == []
