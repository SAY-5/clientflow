import { useState } from "react";
import { evaluate } from "./api";
import { RuleEditor } from "./RuleEditor";
import { newGroup } from "./rules";
import type { EvaluateResult, FieldSpec, Rule, RuleSet } from "./types";

const FIELDS: FieldSpec[] = [
  { name: "amount", type: "number" },
  { name: "country", type: "string" },
  { name: "vip", type: "boolean" },
];

function blankRule(n: number): Rule {
  return {
    id: `rule_${n}`,
    condition: newGroup("and"),
    actions: [{ type: "flag", target: "review", value: "true" }],
  };
}

const STARTER: Rule = {
  id: "high_value_order",
  condition: {
    kind: "group",
    op: "and",
    nodes: [{ kind: "comparison", field: "amount", op: "gte", value: 1000 }],
  },
  actions: [{ type: "flag", target: "review", value: "true" }],
};

export function App() {
  const [rules, setRules] = useState<Rule[]>([STARTER]);
  const [input, setInput] = useState('{\n  "amount": 1500,\n  "country": "US"\n}');
  const [result, setResult] = useState<EvaluateResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ruleSet: RuleSet = {
    name: "demo",
    input_schema: { fields: FIELDS },
    rules,
  };

  function updateRule(idx: number, rule: Rule) {
    setRules(rules.map((r, i) => (i === idx ? rule : r)));
  }

  async function runTest() {
    setError(null);
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(input);
    } catch {
      setError("test input is not valid JSON");
      return;
    }
    try {
      setResult(await evaluate(ruleSet, payload));
    } catch (e) {
      setError(e instanceof Error ? e.message : "evaluation failed");
      setResult(null);
    }
  }

  return (
    <div className="app">
      <header className="masthead">
        <h1>ClientFlow</h1>
        <p>Compose business rules as data and test what fires, no code changes.</p>
      </header>

      <div style={{ marginBottom: "1.5rem" }}>
        {FIELDS.map((f) => (
          <span className="schema-chip" key={f.name}>
            {f.name}: {f.type}
          </span>
        ))}
      </div>

      <div className="grid">
        <section className="panel">
          <h2>Rule set</h2>
          {rules.map((rule, idx) => (
            <RuleEditor
              key={idx}
              rule={rule}
              fields={FIELDS}
              onChange={(r) => updateRule(idx, r)}
              onRemove={() => setRules(rules.filter((_, i) => i !== idx))}
            />
          ))}
          <button
            className="ghost"
            onClick={() => setRules([...rules, blankRule(rules.length + 1)])}
          >
            + add rule
          </button>
        </section>

        <section className="panel">
          <h2>Test input</h2>
          <textarea
            aria-label="test input"
            rows={8}
            style={{ width: "100%", fontFamily: "IBM Plex Mono, monospace" }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <div className="actions-bar">
            <button onClick={runTest}>Run test</button>
          </div>
          {error && <div className="error">{error}</div>}
          {result && (
            <div style={{ marginTop: "1rem" }}>
              <label className="field-label">fired rules</label>
              <div className="fired-list">
                {result.fired.length === 0 ? (
                  <span>none</span>
                ) : (
                  result.fired.map((id) => <span key={id}>{id}</span>)
                )}
              </div>
              <label className="field-label" style={{ marginTop: "0.8rem" }}>
                result
              </label>
              <pre className="data">{JSON.stringify(result.result, null, 2)}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
