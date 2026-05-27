from app.evaluator import evaluate, evaluate_condition, fired_rules
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


def make_rule_set():
    schema = InputSchema(
        fields=[
            FieldSpec(name="amount", type=FieldType.NUMBER),
            FieldSpec(name="country", type=FieldType.STRING),
        ]
    )
    rule = Rule(
        id="high_value",
        condition=Group(
            op="and",
            nodes=[
                Comparison(field="amount", op=Comparator.GTE, value=1000),
                Comparison(field="country", op=Comparator.IN, value=["US", "CA"]),
            ],
        ),
        actions=[Action(type=ActionType.FLAG, target="review", value=True)],
    )
    return RuleSet(name="orders", input_schema=schema, rules=[rule])


def test_comparison_operators():
    assert evaluate_condition(Comparison(field="x", op=Comparator.GT, value=5), {"x": 6})
    assert not evaluate_condition(Comparison(field="x", op=Comparator.GT, value=5), {"x": 4})
    assert evaluate_condition(
        Comparison(field="x", op=Comparator.BETWEEN, value=[1, 10]), {"x": 5}
    )


def test_and_group_requires_all():
    rs = make_rule_set()
    assert fired_rules(rs, {"amount": 1500, "country": "US"})
    assert not fired_rules(rs, {"amount": 1500, "country": "FR"})


def test_or_group_requires_any():
    node = Group(
        op="or",
        nodes=[
            Comparison(field="a", op=Comparator.EQ, value=1),
            Comparison(field="b", op=Comparator.EQ, value=2),
        ],
    )
    assert evaluate_condition(node, {"a": 1, "b": 99})
    assert not evaluate_condition(node, {"a": 0, "b": 0})


def test_matching_rule_fires_its_actions():
    rs = make_rule_set()
    out = evaluate(rs, {"amount": 2000, "country": "CA"})
    assert out["fired"] == ["high_value"]
    assert out["result"]["review"] is True


def test_missing_field_does_not_crash():
    node = Comparison(field="missing", op=Comparator.GT, value=1)
    assert evaluate_condition(node, {"amount": 5}) is False


def test_evaluation_does_not_mutate_input():
    rs = make_rule_set()
    payload = {"amount": 2000, "country": "US"}
    evaluate(rs, payload)
    assert "review" not in payload
