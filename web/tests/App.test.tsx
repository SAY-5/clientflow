import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../src/App";

describe("App", () => {
  it("renders the starter rule and schema fields", () => {
    render(<App />);
    expect(screen.getByText("ClientFlow")).toBeInTheDocument();
    expect(screen.getByDisplayValue("high_value_order")).toBeInTheDocument();
    expect(screen.getByText(/amount: number/)).toBeInTheDocument();
  });
});
