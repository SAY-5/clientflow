import { expect, test } from "@playwright/test";

test("runs a test input against the starter rule and shows it fired", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "ClientFlow" })).toBeVisible();

  // The starter rule flags orders with amount >= 1000. The default test
  // input has amount 1500, so the rule should fire.
  await page.getByRole("button", { name: "Run test" }).click();

  await expect(page.getByText("high_value_order").last()).toBeVisible();
});
