import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.use({ storageState: { cookies: [], origins: [] } });
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [] }),
  );
});

test("first visit explains the demo, guides usage and requires acknowledgment", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const guide = page.getByRole("dialog");
  await expect(guide).toBeVisible();
  await expect(
    guide.getByRole("link", { name: /ดู source code/ }),
  ).toHaveAttribute(
    "href",
    "https://github.com/yousan-nim/Enterprise-Knowledge-Assistant-BasicRAG",
  );
  for (let step = 0; step < 3; step++) {
    await expect(
      guide.getByText(`หน้า ${step + 1} จาก 3`, { exact: false }),
    ).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
    if (step < 2) {
      if (step === 1) await expect(guide.locator("ol li")).toHaveCount(4);
      await guide.getByRole("button", { name: "ถัดไป" }).click();
    }
  }
  const finish = guide.getByRole("button", { name: "รับทราบและเริ่มใช้งาน" });
  await expect(finish).toBeDisabled();
  await guide.getByRole("checkbox").check();
  await guide.getByRole("button", { name: "ย้อนกลับ" }).click();
  await expect(guide.locator("ol li")).toHaveCount(4);
  await guide.getByRole("button", { name: "ถัดไป" }).click();
  await expect(guide.getByRole("checkbox")).toBeChecked();
  await finish.click();
  await expect(guide).not.toBeVisible();
  await page.reload();
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await expect(guide).not.toBeVisible();
  await page.getByRole("button", { name: "About this workspace" }).click();
  await expect(
    guide.getByRole("heading", { name: "ยินดีต้อนรับสู่ Folio" }),
  ).toBeVisible();
});

test("dismissal does not record acknowledgment and API Flows can open the guide", async ({
  page,
}) => {
  await page.goto("/api-flows");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  expect(
    await page.evaluate(() =>
      localStorage.getItem("folio:guide-acknowledged:v1"),
    ),
  ).toBeNull();
  await page.reload();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Close introduction" }).click();
  await page.getByRole("button", { name: "About this workspace" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("disabled browser storage still allows completing the introduction", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => {
      throw new Error("Storage disabled");
    };
    Storage.prototype.setItem = () => {
      throw new Error("Storage disabled");
    };
  });
  await page.goto("/");
  const guide = page.getByRole("dialog");
  await guide.getByRole("button", { name: "ถัดไป" }).click();
  await guide.getByRole("button", { name: "ถัดไป" }).click();
  await guide.getByRole("checkbox").check();
  await guide.getByRole("button", { name: "รับทราบและเริ่มใช้งาน" }).click();
  await expect(guide).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "About this workspace" }),
  ).toBeEnabled();
});
