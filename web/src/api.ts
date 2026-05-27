import type { EvaluateResult, RuleSet } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function evaluate(
  ruleSet: RuleSet,
  payload: Record<string, unknown>,
): Promise<EvaluateResult> {
  const res = await fetch(`${BASE}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rule_set: ruleSet, payload }),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? `request failed: ${res.status}`);
  }
  return (await res.json()) as EvaluateResult;
}
