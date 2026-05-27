import type { Comparator, Comparison, Condition, FieldType, Group } from "./types";

export const COMPARATORS: Comparator[] = [
  "eq",
  "ne",
  "gt",
  "gte",
  "lt",
  "lte",
  "in",
  "not_in",
  "between",
];

const NUMERIC_OPS: Comparator[] = ["gt", "gte", "lt", "lte", "between"];

export function newComparison(field: string): Comparison {
  return { kind: "comparison", field, op: "eq", value: "" };
}

export function newGroup(op: "and" | "or" = "and"): Group {
  return { kind: "group", op, nodes: [] };
}

/** Coerce a raw text input into the value an operator and field type expect. */
export function coerceValue(
  raw: string,
  op: Comparator,
  fieldType: FieldType,
): unknown {
  if (op === "in" || op === "not_in") {
    return splitList(raw, fieldType);
  }
  if (op === "between") {
    return splitList(raw, "number").slice(0, 2);
  }
  return coerceScalar(raw, fieldType);
}

function splitList(raw: string, fieldType: FieldType): unknown[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map((s) => coerceScalar(s, fieldType));
}

function coerceScalar(raw: string, fieldType: FieldType): unknown {
  if (fieldType === "number") {
    const n = Number(raw);
    return Number.isNaN(n) ? raw : n;
  }
  if (fieldType === "boolean") {
    return raw === "true";
  }
  return raw;
}

/** Operators valid for a given field type, used to drive the builder UI. */
export function allowedOperators(fieldType: FieldType): Comparator[] {
  if (fieldType === "number") {
    return COMPARATORS;
  }
  return COMPARATORS.filter((op) => !NUMERIC_OPS.includes(op));
}

export function isGroup(node: Condition): node is Group {
  return node.kind === "group";
}
