export type Comparator =
  | "eq"
  | "ne"
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "in"
  | "not_in"
  | "between";

export type FieldType = "number" | "string" | "boolean";

export interface FieldSpec {
  name: string;
  type: FieldType;
}

export interface Comparison {
  kind: "comparison";
  field: string;
  op: Comparator;
  value: unknown;
}

export interface Group {
  kind: "group";
  op: "and" | "or";
  nodes: Condition[];
}

export type Condition = Comparison | Group;

export type ActionType = "set" | "route" | "flag";

export interface Action {
  type: ActionType;
  target: string;
  value: unknown;
}

export interface Rule {
  id: string;
  description?: string;
  condition: Condition;
  actions: Action[];
  triggers?: string[];
}

export interface RuleSet {
  name: string;
  input_schema: { fields: FieldSpec[] };
  rules: Rule[];
}

export interface EvaluateResult {
  fired: string[];
  actions: Action[];
  result: Record<string, unknown>;
}
