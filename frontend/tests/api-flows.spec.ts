import { test, expect } from "@playwright/test";

test("navbar opens current API diagrams and returns to the workspace on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "API Flows" })
    .click();
  await expect(page).toHaveURL(/\/api-flows$/);
  await expect(
    page.getByRole("link", { name: "API Flows", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  const diagram = page.frameLocator(
    'iframe[title="Six API endpoint process diagrams"]',
  );
  await expect(diagram.locator("section")).toHaveCount(6);
  await expect(
    diagram.getByText("Native GPU mode (เครื่องนี้):", { exact: true }),
  ).toBeVisible();
  await expect(
    diagram.locator("code").filter({ hasText: "host.docker.internal:11434" }),
  ).toBeVisible();
  await diagram
    .getByRole("link", { name: "05 Questions / RAG", exact: true })
    .click();
  await expect(diagram.locator("#questions h2")).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Workspace", exact: true })
    .click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByLabel("Ask your document", { exact: true }),
  ).toBeVisible();
});
