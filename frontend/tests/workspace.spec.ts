import { expect, test } from "@playwright/test";
const indexedDocument = {
  document_id: "test-document",
  source: "policy.pdf",
  embedding_model: "embeddinggemma",
  chunks: 2,
};
const source = {
  id: "chunk-1",
  text: "ค่าเดินทางเบิกได้สูงสุด 500 บาทต่อวัน โดยต้องแนบใบเสร็จ",
  source: "policy.pdf",
  page: 2,
  extraction_method: "ocr",
  score: 0.72,
};

test("uploads, asks, inspects evidence and removes a document", async ({
  page,
}) => {
  let indexed = false;
  let removed = false;
  await page.route("**/api/v1/documents", async (route) => {
    if (route.request().method() === "POST") {
      indexed = true;
      await route.fulfill({
        status: 201,
        json: {
          document_id: indexedDocument.document_id,
          source: indexedDocument.source,
          chunks: 2,
        },
      });
    } else await route.fulfill({ json: indexed ? [indexedDocument] : [] });
  });
  await page.route("**/api/v1/questions", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      question: "ค่าเดินทางเท่าไร?",
      top_k: 3,
    });
    await route.fulfill({
      json: {
        answer: "เบิกได้สูงสุด 500 บาทต่อวัน และต้องแนบใบเสร็จ",
        citation_ids: ["chunk-1"],
        found: true,
        sources: [source],
      },
    });
  });
  await page.route("**/api/v1/documents/test-document", async (route) => {
    removed = true;
    indexed = false;
    await route.fulfill({ status: 204 });
  });
  await page.goto("/");
  await expect(page.getByRole("status").first()).toContainText("API connected");
  await expect(
    page.getByRole("button", { name: "Send question" }),
  ).toBeDisabled();
  await page
    .getByLabel("Upload a PDF, TXT or Markdown document")
    .setInputFiles({
      name: "policy.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("fixture"),
    });
  await expect(page.getByText("policy.pdf is ready.")).toBeVisible();
  await page
    .getByLabel("Ask your document", { exact: true })
    .fill("ค่าเดินทางเท่าไร?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.getByText("เบิกได้สูงสุด 500 บาทต่อวัน และต้องแนบใบเสร็จ", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "1 cited passage" }).click();
  await expect(page.getByText("Page 2", { exact: false })).toBeVisible();
  await expect(page.getByText("Read with OCR")).toBeVisible();
  await expect(page.getByText("Similarity 0.72")).toBeVisible();
  await page.getByRole("button", { name: "Remove policy.pdf" }).click();
  await page.getByRole("button", { name: "Keep it", exact: true }).click();
  expect(removed).toBeFalsy();
  await page.getByRole("button", { name: "Remove policy.pdf" }).click();
  await page.getByRole("button", { name: "Remove", exact: true }).click();
  await expect(
    page.getByText("Document removed. A fresh page awaits."),
  ).toBeVisible();
  expect(removed).toBeTruthy();
  await expect(
    page.getByRole("button", { name: "Send question" }),
  ).toBeDisabled();
});

test("replacement needs confirmation and failed indexing keeps the existing document", async ({
  page,
}) => {
  let writes = 0;
  await page.route("**/api/v1/documents", async (route) => {
    if (route.request().method() === "POST") {
      writes++;
      await route.fulfill({
        status: 422,
        json: { detail: "OCR could not read this page." },
      });
    } else await route.fulfill({ json: [indexedDocument] });
  });
  await page.goto("/");
  await expect(page.getByText("2 passages")).toBeVisible();
  await page
    .getByLabel("Upload a PDF, TXT or Markdown document")
    .setInputFiles({
      name: "new.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("fixture"),
    });
  await expect(page.getByText("Replace your document?")).toBeVisible();
  expect(writes).toBe(0);
  await page.getByRole("button", { name: "Replace", exact: true }).click();
  await expect(
    page
      .getByRole("region", { name: "Conversation", exact: true })
      .getByRole("alert"),
  ).toContainText("OCR could not read");
  expect(writes).toBe(1);
  await expect(page.getByText("policy.pdf", { exact: true })).toBeVisible();
});

test("validates files and allows direct chat without a document", async ({
  page,
}) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/v1/chat", (route) =>
    route.fulfill({ json: { answer: "Let’s explore that idea." } }),
  );
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page
    .getByLabel("Upload a PDF, TXT or Markdown document")
    .setInputFiles({
      name: "photo.png",
      mimeType: "image/png",
      buffer: Buffer.from("fixture"),
    });
  await expect(
    page
      .getByRole("region", { name: "Conversation", exact: true })
      .getByRole("alert"),
  ).toContainText("Choose a PDF, TXT or Markdown file.");
  await page.getByRole("button", { name: "Free chat", exact: true }).click();
  await page.getByLabel("Ask Folio", { exact: true }).fill("Hello");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Let’s explore that idea.")).toBeVisible();
  await expect(page.getByRole("button", { name: /cited passage/ })).toHaveCount(
    0,
  );
});

test("handles unavailable backend and empty answers without invented certainty", async ({
  page,
}) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ status: 503, json: { detail: "Database unavailable." } }),
  );
  await page.goto("/");
  await expect(
    page
      .getByRole("region", { name: "Conversation", exact: true })
      .getByRole("alert"),
  ).toContainText("Database unavailable.");
  await expect(
    page.getByText("API unavailable", { exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/v1/documents");
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [indexedDocument] }),
  );
  await page.getByRole("button", { name: "Refresh document list" }).click();
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page.route("**/api/v1/questions", (route) =>
    route.fulfill({
      json: {
        answer: "ไม่พบข้อมูลในเอกสาร",
        found: false,
        citation_ids: [],
        sources: [source],
      },
    }),
  );
  await page
    .getByLabel("Ask your document", { exact: true })
    .fill("What about lunch?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Not found in document")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Review retrieved passages" }),
  ).toBeVisible();
});

test("mobile layout fits, supports keyboard input and exposes the about dialog", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [indexedDocument] }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Document Q&A" }),
  ).toBeVisible();
  const sizes = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    viewport: innerWidth,
  }));
  expect(sizes.page).toBeLessThanOrEqual(sizes.viewport);
  await page.getByRole("button", { name: "About this workspace" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .getByLabel("Ask your document", { exact: true })
    .fill("First line");
  await page
    .getByLabel("Ask your document", { exact: true })
    .press("Shift+Enter");
  await expect(
    page.getByLabel("Ask your document", { exact: true }),
  ).toHaveValue("First line\n");
});

test("drag and drop uses the same real upload flow", async ({ page }) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill(
      route.request().method() === "POST"
        ? {
            status: 201,
            json: { document_id: "drop-id", source: "notes.txt", chunks: 1 },
          }
        : { json: [] },
    ),
  );
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  const transfer = await page.evaluateHandle(() => {
    const value = new DataTransfer();
    value.items.add(
      new File(["Travel policy"], "notes.txt", { type: "text/plain" }),
    );
    return value;
  });
  await page
    .locator(".upload-zone")
    .dispatchEvent("drop", { dataTransfer: transfer });
  await expect(
    page.getByText("notes.txt is ready. Ask your first question."),
  ).toBeVisible();
});

test("question errors restore input and prevent duplicate requests while pending", async ({
  page,
}) => {
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ json: [indexedDocument] }),
  );
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/questions", async (route) => {
    await gate;
    await route.fulfill({
      status: 503,
      json: { detail: "Model is unavailable." },
    });
  });
  await page.goto("/");
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
  await page
    .getByLabel("Ask your document", { exact: true })
    .fill("Please retry this question.");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.getByRole("button", { name: "Send question" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Free chat", exact: true }),
  ).toBeDisabled();
  release();
  await expect(
    page
      .getByRole("region", { name: "Conversation", exact: true })
      .getByRole("alert"),
  ).toContainText("Model is unavailable.");
  await expect(
    page.getByLabel("Ask your document", { exact: true }),
  ).toHaveValue("Please retry this question.");
  await expect(page.getByRole("button", { name: /cited passage/ })).toHaveCount(
    0,
  );
});
