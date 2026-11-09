import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
test("workspace has no WCAG A/AA accessibility violations", async ({
  page,
}) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});
test("all responsive layouts stay within the viewport", async ({ page }) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  for (const width of [360, 390, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    const size = await page.evaluate(() => ({
      actual: document.documentElement.scrollWidth,
      viewport: innerWidth,
    }));
    expect(size.actual, `overflow at ${width}px`).toBeLessThanOrEqual(
      size.viewport,
    );
  }
});
