"""Rule set validation and cycle detection.

Before a rule set goes active it is checked against its declared input
schema. The checks reject malformed rules with a clear message and
detect cycles in rule chains so a self triggering set cannot loop
forever at evaluation time.
"""

from __future__ import annotations

from .models import (
    Action,
    ActionType,
    Comparator,
    Comparison,
    Condition,
    FieldType,
    Group,
    Rule,
    RuleSet,
)


class ValidationError(Exception):
    """Raised when a rule set is not safe to activate."""


_NUMERIC_OPS = {
    Comparator.GT,
    Comparator.GTE,
    Comparator.LT,
    Comparator.LTE,
    Comparator.BETWEEN,
}


def _check_comparison(rule_id: str, node: Comparison, fields: dict[str, FieldType]) -> None:
    if node.field not in fields:
        raise ValidationError(
            f"rule '{rule_id}' references unknown field '{node.field}'"
        )
    ftype = fields[node.field]
    if node.op in _NUMERIC_OPS and ftype is not FieldType.NUMBER:
        raise ValidationError(
            f"rule '{rule_id}' uses numeric operator '{node.op.value}' "
            f"on non numeric field '{node.field}'"
        )
    if node.op is Comparator.BETWEEN:
        if not isinstance(node.value, list) or len(node.value) != 2:
            raise ValidationError(
                f"rule '{rule_id}' between on '{node.field}' needs a two element list"
            )
    if node.op in (Comparator.IN, Comparator.NOT_IN):
        if not isinstance(node.value, list):
            raise ValidationError(
                f"rule '{rule_id}' operator '{node.op.value}' on '{node.field}' "
                f"needs a list value"
            )


def _check_condition(rule_id: str, node: Condition, fields: dict[str, FieldType]) -> None:
    if isinstance(node, Comparison):
        _check_comparison(rule_id, node, fields)
        return
    if isinstance(node, Group):
        if not node.nodes:
            raise ValidationError(f"rule '{rule_id}' has an empty '{node.op}' group")
        for child in node.nodes:
            _check_condition(rule_id, child, fields)
        return
    raise ValidationError(f"rule '{rule_id}' has an unknown condition node")


def _check_action(rule_id: str, action: Action) -> None:
    if not action.target:
        raise ValidationError(f"rule '{rule_id}' has an action with no target")
    if action.type is ActionType.SET and action.value is None:
        raise ValidationError(
            f"rule '{rule_id}' set action on '{action.target}' has no value"
        )


def _condition_fields(node: Condition, out: set[str]) -> None:
    if isinstance(node, Comparison):
        out.add(node.field)
    elif isinstance(node, Group):
        for child in node.nodes:
            _condition_fields(child, out)


def detect_cycle(rules: list[Rule]) -> list[str] | None:
    """Detect a cycle in rule chaining.

    An edge runs from rule A to rule B when A declares a trigger field
    that B reads in its condition. A cycle in that graph means evaluation
    could loop, so it is rejected. Returns the cycle as a list of rule
    ids, or None when the graph is acyclic.
    """
    reads: dict[str, set[str]] = {}
    for rule in rules:
        fields: set[str] = set()
        _condition_fields(rule.condition, fields)
        reads[rule.id] = fields

    graph: dict[str, set[str]] = {r.id: set() for r in rules}
    for src in rules:
        for dst in rules:
            if src.id == dst.id:
                continue
            if set(src.triggers) & reads.get(dst.id, set()):
                graph[src.id].add(dst.id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = GRAY
        stack.append(node)
        for nxt in graph[node]:
            if color[nxt] == GRAY:
                idx = stack.index(nxt)
                return stack[idx:] + [nxt]
            if color[nxt] == WHITE:
                found = visit(nxt)
                if found is not None:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for node in graph:
        if color[node] == WHITE:
            found = visit(node)
            if found is not None:
                return found
    return None


def validate_rule_set(rule_set: RuleSet) -> None:
    """Validate a rule set or raise ValidationError with a clear message."""
    fields = rule_set.input_schema.field_map()
    seen: set[str] = set()
    for rule in rule_set.rules:
        if rule.id in seen:
            raise ValidationError(f"duplicate rule id '{rule.id}'")
        seen.add(rule.id)
        _check_condition(rule.id, rule.condition, fields)
        if not rule.actions:
            raise ValidationError(f"rule '{rule.id}' has no actions")
        for action in rule.actions:
            _check_action(rule.id, action)

    cycle = detect_cycle(rule_set.rules)
    if cycle is not None:
        raise ValidationError("cyclic rule chain detected: " + " -> ".join(cycle))
