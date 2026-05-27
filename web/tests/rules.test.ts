import { describe, expect, it } from "vitest";
import { allowedOperators, coerceValue } from "../src/rules";

describe("coerceValue", () => {
  it("parses numbers for numeric fields", () => {
    expect(coerceValue("42", "gte", "number")).toBe(42);
  });

  it("keeps strings as strings", () => {
    expect(coerceValue("US", "eq", "string")).toBe("US");
  });

  it("splits a comma list for in operator", () => {
    expect(coerceValue("US, CA", "in", "string")).toEqual(["US", "CA"]);
  });

  it("takes two numbers for between", () => {
    expect(coerceValue("10, 20, 30", "between", "number")).toEqual([10, 20]);
  });
});

describe("allowedOperators", () => {
  it("hides numeric operators for string fields", () => {
    expect(allowedOperators("string")).not.toContain("gt");
  });

  it("offers numeric operators for number fields", () => {
    expect(allowedOperators("number")).toContain("between");
  });
});
