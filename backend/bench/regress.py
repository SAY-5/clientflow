"""Benchmark regression gate.

Runs the benchmark and compares throughput against a stored baseline.
The gate fails if throughput drops more than the allowed fraction below
the baseline. This is a smoke gate, not a precise measurement, so the
tolerance is wide enough to absorb runner to runner variation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bench.benchmark import run

BASELINE = Path(__file__).parent / "baseline.json"
TOLERANCE = 0.30


def main() -> int:
    baseline = json.loads(BASELINE.read_text())
    floor = baseline["evals_per_second"] * (1 - TOLERANCE)

    result = run(
        num_rules=baseline["rules"],
        num_inputs=baseline["inputs"],
    )
    measured = result["evals_per_second"]

    print(f"baseline {baseline['evals_per_second']:.0f} evals/s")
    print(f"floor    {floor:.0f} evals/s (baseline minus {int(TOLERANCE * 100)}%)")
    print(f"measured {measured:.0f} evals/s")

    if measured < floor:
        print("regression detected")
        return 1
    print("within tolerance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
