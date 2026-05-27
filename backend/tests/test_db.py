"""Storage tests. Skipped automatically when no database is reachable."""

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


def make_rule_set(name: str) -> RuleSet:
    return RuleSet(
        name=name,
        input_schema=InputSchema(fields=[FieldSpec(name="amount", type=FieldType.NUMBER)]),
        rules=[
            Rule(
                id="big",
                condition=Comparison(field="amount", op=Comparator.GTE, value=1000),
                actions=[Action(type=ActionType.FLAG, target="review", value=True)],
            )
        ],
    )


def test_save_and_activate_round_trip():
    name = f"rs_{uuid.uuid4().hex[:8]}"
    rs = make_rule_set(name)
    v1 = service.save_rule_set(rs)
    service.activate(name, v1)
    out = service.run_active(name, {"amount": 2000})
    assert out["fired"] == ["big"]


def test_run_active_with_no_active_version_raises():
    name = f"rs_{uuid.uuid4().hex[:8]}"
    with pytest.raises(KeyError):
        service.run_active(name, {"amount": 1})
