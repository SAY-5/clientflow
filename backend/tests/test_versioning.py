"""Versioning and dry-run tests. Skipped when no database is reachable."""

import os
import uuid

import psycopg
import pytest

from app import db, service
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


def _db_available() -> bool:
    try:
        with psycopg.connect(db.DATABASE_URL, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available() and not os.environ.get("REQUIRE_DB"),
    reason="no database reachable",
)


@pytest.fixture(autouse=True)
def schema():
    db.init_db()


def rule_set(name: str, threshold: int) -> RuleSet:
    return RuleSet(
        name=name,
        input_schema=InputSchema(fields=[FieldSpec(name="amount", type=FieldType.NUMBER)]),
        rules=[
            Rule(
                id="big",
                condition=Comparison(field="amount", op=Comparator.GTE, value=threshold),
                actions=[Action(type=ActionType.FLAG, target="review", value=True)],
            )
        ],
    )


def test_each_save_creates_a_new_version():
    name = f"rs_{uuid.uuid4().hex[:8]}"
    v1 = service.save_rule_set(rule_set(name, 1000))
    v2 = service.save_rule_set(rule_set(name, 2000))
    assert [v1, v2] == [1, 2]
    assert db.list_versions(name) == [1, 2]


def test_activation_switches_pointer_and_prior_version_remains():
    name = f"rs_{uuid.uuid4().hex[:8]}"
    v1 = service.save_rule_set(rule_set(name, 1000))
    v2 = service.save_rule_set(rule_set(name, 2000))

    service.activate(name, v1)
    assert db.active_version_number(name) == v1
    # threshold 1000: an order of 1500 fires.
    assert service.run_active(name, {"amount": 1500})["fired"] == ["big"]

    service.activate(name, v2)
    assert db.active_version_number(name) == v2
    # threshold 2000: the same order no longer fires.
    assert service.run_active(name, {"amount": 1500})["fired"] == []

    # the prior version is still retrievable.
    prior = service.get_rule_set_version(name, v1)
    assert prior is not None
    assert prior.rules[0].condition.value == 1000


def test_activating_unknown_version_raises():
    name = f"rs_{uuid.uuid4().hex[:8]}"
    service.save_rule_set(rule_set(name, 1000))
    with pytest.raises(KeyError):
        service.activate(name, 99)


def test_dry_run_does_not_change_active_version():
    name = f"rs_{uuid.uuid4().hex[:8]}"
    v1 = service.save_rule_set(rule_set(name, 1000))
    v2 = service.save_rule_set(rule_set(name, 5000))
    service.activate(name, v1)

    # dry-run the candidate v2 against an input. v2 should not fire at 1500.
    out = service.dry_run(name, v2, {"amount": 1500})
    assert out["fired"] == []

    # the active version is unchanged and still behaves like v1.
    assert db.active_version_number(name) == v1
    assert service.run_active(name, {"amount": 1500})["fired"] == ["big"]
