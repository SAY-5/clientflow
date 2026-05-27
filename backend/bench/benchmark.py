"""Benchmark evaluating a large rule set against many inputs.

Builds a rule set of N rules over a few numeric fields and evaluates M
random inputs against it, reporting evaluations per second. The number
is measured at run time; nothing here is hard coded.

Usage:
    python -m bench.benchmark            # human readable
    python -m bench.benchmark --json     # machine readable for CI
"""

from __future__ import annotations

import argparse
import json
import random
import time

from app.evaluator import evaluate
from app.models import (
    Action,
    ActionType,
    Comparator,
    Comparison,
    Condition,
    FieldSpec,
    FieldType,
    Group,
    InputSchema,
    Rule,
    RuleSet,
)

FIELDS = ["a", "b", "c", "d"]


def build_rule_set(num_rules: int, rng: random.Random) -> RuleSet:
    rules = []
    ops = [Comparator.GT, Comparator.LT, Comparator.GTE, Comparator.LTE, Comparator.EQ]
    for i in range(num_rules):
        nodes: list[Condition] = [
            Comparison(
                field=rng.choice(FIELDS),
                op=rng.choice(ops),
                value=rng.randint(0, 100),
            )
            for _ in range(3)
        ]
        rules.append(
            Rule(
                id=f"rule_{i}",
                condition=Group(op=rng.choice(["and", "or"]), nodes=nodes),
                actions=[Action(type=ActionType.FLAG, target=f"hit_{i}", value=True)],
            )
        )
    schema = InputSchema(fields=[FieldSpec(name=f, type=FieldType.NUMBER) for f in FIELDS])
    return RuleSet(name="bench", input_schema=schema, rules=rules)


def build_inputs(num_inputs: int, rng: random.Random) -> list[dict[str, int]]:
    return [{f: rng.randint(0, 100) for f in FIELDS} for _ in range(num_inputs)]


def run(num_rules: int = 500, num_inputs: int = 2000, seed: int = 7) -> dict[str, float]:
    rng = random.Random(seed)
    rule_set = build_rule_set(num_rules, rng)
    inputs = build_inputs(num_inputs, rng)

    start = time.perf_counter()
    for payload in inputs:
        evaluate(rule_set, payload)
    elapsed = time.perf_counter() - start

    evals = num_inputs
    return {
        "rules": num_rules,
        "inputs": num_inputs,
        "seconds": elapsed,
        "evals_per_second": evals / elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rules", type=int, default=500)
    parser.add_argument("--inputs", type=int, default=2000)
    args = parser.parse_args()

    result = run(num_rules=args.rules, num_inputs=args.inputs)
    if args.json:
        print(json.dumps(result))
    else:
        print(
            f"{result['inputs']} inputs against {result['rules']} rules "
            f"in {result['seconds']:.3f}s "
            f"({result['evals_per_second']:.0f} evaluations per second)"
        )


if __name__ == "__main__":
    main()
