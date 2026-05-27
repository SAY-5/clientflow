"""Safe, bounded rule evaluator.

The evaluator walks a typed condition tree and never calls eval/exec on
user content. Conditions are interpreted node by node. Any field access
or comparison that cannot be performed safely returns False for that
node rather than raising, so no input payload can crash evaluation.
"""

from __future__ import annotations

from typing import Any

from .models import (
    Action,
    Comparator,
    Comparison,
    Condition,
    Group,
    Rule,
    RuleSet,
)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _compare(op: Comparator, left: Any, right: Any) -> bool:
    if op is Comparator.EQ:
        return left == right
    if op is Comparator.NE:
        return left != right
    if op in (Comparator.GT, Comparator.GTE, Comparator.LT, Comparator.LTE):
        ln, rn = _as_number(left), _as_number(right)
        if ln is None or rn is None:
            return False
        if op is Comparator.GT:
            return ln > rn
        if op is Comparator.GTE:
            return ln >= rn
        if op is Comparator.LT:
            return ln < rn
        return ln <= rn
    if op is Comparator.IN:
        return isinstance(right, list) and left in right
    if op is Comparator.NOT_IN:
        return isinstance(right, list) and left not in right
    if op is Comparator.BETWEEN:
        if not isinstance(right, list) or len(right) != 2:
            return False
        ln = _as_number(left)
        lo, hi = _as_number(right[0]), _as_number(right[1])
        if ln is None or lo is None or hi is None:
            return False
        return lo <= ln <= hi
    return False


def evaluate_condition(node: Condition, payload: dict[str, Any]) -> bool:
    """Return whether a condition node matches the payload."""
    if isinstance(node, Comparison):
        if node.field not in payload:
            return False
        return _compare(node.op, payload[node.field], node.value)
    if isinstance(node, Group):
        results = (evaluate_condition(child, payload) for child in node.nodes)
        if node.op == "and":
            return all(results)
        return any(results)
    return False


def apply_action(action: Action, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a new payload with the action applied. Does not mutate input."""
    updated = dict(payload)
    updated[action.target] = action.value
    return updated


def evaluate(rule_set: RuleSet, payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a payload against a rule set.

    Returns the rules that fired, the actions applied and the resulting
    payload. Evaluation is deterministic for a given input and rule set:
    rules are processed in declared order and a later rule sees the
    output of earlier ones.
    """
    working = dict(payload)
    fired: list[str] = []
    applied: list[Action] = []
    for rule in rule_set.rules:
        if evaluate_condition(rule.condition, working):
            fired.append(rule.id)
            for action in rule.actions:
                applied.append(action)
                working = apply_action(action, working)
    return {
        "fired": fired,
        "actions": [a.model_dump() for a in applied],
        "result": working,
    }


def fired_rules(rule_set: RuleSet, payload: dict[str, Any]) -> list[Rule]:
    """Return the list of rules whose condition matches the payload as-is."""
    return [r for r in rule_set.rules if evaluate_condition(r.condition, payload)]
