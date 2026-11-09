import { createServer, type Server } from "node:http";
import { expect, test } from "@playwright/test";
let server: Server;
let calls = 0;
test.beforeAll(async () => {
  server = createServer(async (req, res) => {
    calls++;
    const buffers: Buffer[] = [];
    for await (const part of req) buffers.push(Buffer.from(part));
    const body = Buffer.concat(buffers).toString();
    if (req.method === "DELETE") {
      res.writeHead(204);
      res.end();
      return;
    }
    res.setHeader("Content-Type", "application/json");
    if (req.url === "/api/v1/questions") {
      res.writeHead(503);
      res.end(JSON.stringify({ detail: "Model unavailable." }));
      return;
    }
    res.end(
      JSON.stringify({
        path: req.url,
        method: req.method,
        contentType: req.headers["content-type"],
        body,
      }),
    );
  });
  await new Promise<void>((resolve) =>
    server.listen(18081, "127.0.0.1", resolve),
  );
});
test.afterAll(async () => {
  await new Promise<void>((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
});
test("same-origin proxy preserves multipart, status codes and restricts routes", async ({
  request,
}) => {
  const upload = await request.post("/api/v1/documents", {
    multipart: {
      file: {
        name: "ภาษาไทย.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("ข้อมูลทดสอบ"),
      },
    },
  });
  expect(upload.status()).toBe(200);
  const data = await upload.json();
  expect(data.path).toBe("/api/v1/documents");
  expect(data.method).toBe("POST");
  expect(data.contentType).toContain("multipart/form-data; boundary=");
  expect(data.body).toContain("ข้อมูลทดสอบ");
  const remove = await request.delete("/api/v1/documents/test-id");
  expect(remove.status()).toBe(204);
  expect(await remove.body()).toHaveLength(0);
  const error = await request.post("/api/v1/questions", {
    data: { question: "test" },
  });
  expect(error.status()).toBe(503);
  expect(await error.json()).toEqual({ detail: "Model unavailable." });
  const before = calls;
  const denied = await request.get("/api/private");
  expect(denied.status()).toBe(404);
  expect(calls).toBe(before);
  const large = await request.post("/api/v1/documents", {
    data: Buffer.alloc(2 * 1024 * 1024 + 1),
  });
  expect(large.status()).toBe(413);
  expect(calls).toBe(before);
});
