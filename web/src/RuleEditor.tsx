import type { Comparison, FieldSpec, Group, Rule } from "./types";
import {
  allowedOperators,
  coerceValue,
  newComparison,
} from "./rules";

interface Props {
  rule: Rule;
  fields: FieldSpec[];
  onChange: (rule: Rule) => void;
  onRemove: () => void;
}

function fieldType(fields: FieldSpec[], name: string) {
  return fields.find((f) => f.name === name)?.type ?? "string";
}

function rawOf(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (value === null || value === undefined) return "";
  return String(value);
}

export function RuleEditor({ rule, fields, onChange, onRemove }: Props) {
  const group = rule.condition as Group;

  function updateComparison(idx: number, next: Comparison) {
    const nodes = group.nodes.slice();
    nodes[idx] = next;
    onChange({ ...rule, condition: { ...group, nodes } });
  }

  function addCondition() {
    const field = fields[0]?.name ?? "";
    const nodes = [...group.nodes, newComparison(field)];
    onChange({ ...rule, condition: { ...group, nodes } });
  }

  function removeCondition(idx: number) {
    const nodes = group.nodes.filter((_, i) => i !== idx);
    onChange({ ...rule, condition: { ...group, nodes } });
  }

  return (
    <div className="rule">
      <div className="rule-head">
        <input
          className="rule-id"
          value={rule.id}
          aria-label="rule id"
          onChange={(e) => onChange({ ...rule, id: e.target.value })}
        />
        <button className="ghost tiny" onClick={onRemove}>
          remove rule
        </button>
      </div>

      <label className="field-label">match</label>
      <select
        aria-label="group operator"
        value={group.op}
        onChange={(e) =>
          onChange({
            ...rule,
            condition: { ...group, op: e.target.value as "and" | "or" },
          })
        }
      >
        <option value="and">all of (AND)</option>
        <option value="or">any of (OR)</option>
      </select>

      {group.nodes.map((node, idx) => {
        const cmp = node as Comparison;
        const ftype = fieldType(fields, cmp.field);
        return (
          <div className="condition-row" key={idx}>
            <select
              aria-label="field"
              value={cmp.field}
              onChange={(e) =>
                updateComparison(idx, { ...cmp, field: e.target.value })
              }
            >
              {fields.map((f) => (
                <option key={f.name} value={f.name}>
                  {f.name}
                </option>
              ))}
            </select>
            <select
              aria-label="operator"
              value={cmp.op}
              onChange={(e) =>
                updateComparison(idx, {
                  ...cmp,
                  op: e.target.value as Comparison["op"],
                })
              }
            >
              {allowedOperators(ftype).map((op) => (
                <option key={op} value={op}>
                  {op}
                </option>
              ))}
            </select>
            <input
              className="value"
              aria-label="value"
              value={rawOf(cmp.value)}
              onChange={(e) =>
                updateComparison(idx, {
                  ...cmp,
                  value: coerceValue(e.target.value, cmp.op, ftype),
                })
              }
            />
            <button className="ghost tiny" onClick={() => removeCondition(idx)}>
              x
            </button>
          </div>
        );
      })}

      <button className="ghost tiny" onClick={addCondition}>
        + condition
      </button>

      <label className="field-label" style={{ marginTop: "0.7rem" }}>
        then
      </label>
      {rule.actions.map((action, idx) => (
        <div className="action-row" key={idx}>
          <select
            aria-label="action type"
            value={action.type}
            onChange={(e) => {
              const actions = rule.actions.slice();
              actions[idx] = {
                ...action,
                type: e.target.value as typeof action.type,
              };
              onChange({ ...rule, actions });
            }}
          >
            <option value="flag">flag</option>
            <option value="set">set</option>
            <option value="route">route</option>
          </select>
          <input
            aria-label="action target"
            placeholder="target"
            value={action.target}
            onChange={(e) => {
              const actions = rule.actions.slice();
              actions[idx] = { ...action, target: e.target.value };
              onChange({ ...rule, actions });
            }}
          />
          <input
            aria-label="action value"
            placeholder="value"
            value={rawOf(action.value)}
            onChange={(e) => {
              const actions = rule.actions.slice();
              actions[idx] = { ...action, value: e.target.value };
              onChange({ ...rule, actions });
            }}
          />
        </div>
      ))}
    </div>
  );
}
