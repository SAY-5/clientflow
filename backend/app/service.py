"""Service layer tying storage, validation and evaluation together."""

from __future__ import annotations

from typing import Any

from . import db
from .evaluator import evaluate
from .models import RuleSet
from .validation import validate_rule_set


def save_rule_set(rule_set: RuleSet) -> int:
    """Validate and store a new version. Does not activate it."""
    validate_rule_set(rule_set)
    return db.save_version(rule_set.name, rule_set.model_dump())


def activate(name: str, version: int) -> None:
    db.activate_version(name, version)


def get_active_rule_set(name: str) -> RuleSet | None:
    body = db.get_active(name)
    return RuleSet.model_validate(body) if body else None


def get_rule_set_version(name: str, version: int) -> RuleSet | None:
    body = db.get_version(name, version)
    return RuleSet.model_validate(body) if body else None


def run_active(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    rule_set = get_active_rule_set(name)
    if rule_set is None:
        raise KeyError(f"no active rule set named '{name}'")
    return evaluate(rule_set, payload)


def dry_run(name: str, version: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a stored version against an input without activating it."""
    rule_set = get_rule_set_version(name, version)
    if rule_set is None:
        raise KeyError(f"version {version} of '{name}' does not exist")
    return evaluate(rule_set, payload)
