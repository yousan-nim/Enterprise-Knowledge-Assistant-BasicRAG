import { NextRequest } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const MAX_BODY = 2 * 1024 * 1024;
type Context = { params: Promise<{ path: string[] }> };
async function proxy(request: NextRequest, context: Context) {
  const { path } = await context.params;
  const route = path.join("/");
  if (
    !/^v1\/(health|documents|questions|chat)$/.test(route) &&
    !/^v1\/documents\/[^/]+$/.test(route)
  ) {
    return Response.json({ detail: "Endpoint not found." }, { status: 404 });
  }
  let body: ArrayBuffer | undefined;
  if (request.body) {
    const reader = request.body.getReader();
    const parts: Uint8Array[] = [];
    let length = 0;
    while (true) {
      const result = await reader.read();
      if (result.done) break;
      length += result.value.byteLength;
      if (length > MAX_BODY) {
        await reader.cancel();
        return Response.json(
          { detail: "Request is too large." },
          { status: 413 },
        );
      }
      parts.push(result.value);
    }
    body = new ArrayBuffer(length);
    const bytes = new Uint8Array(body);
    let offset = 0;
    for (const part of parts) {
      bytes.set(part, offset);
      offset += part.length;
    }
  }
  const base = process.env.BACKEND_URL || "http://127.0.0.1:8080";
  try {
    const response = await fetch(
      `${base.replace(/\/$/, "")}/api/${path.map(encodeURIComponent).join("/")}`,
      {
        method: request.method,
        body,
        cache: "no-store",
        redirect: "manual",
        headers: {
          "Content-Type":
            request.headers.get("Content-Type") || "application/json",
        },
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(600_000)]),
      },
    );
    return new Response(response.status === 204 ? null : response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const timeout =
      error instanceof Error &&
      ["TimeoutError", "AbortError"].includes(error.name);
    return Response.json(
      {
        detail: timeout
          ? "The request took too long. Please check your document before retrying."
          : "Cannot reach the knowledge service. Start the backend and try again.",
      },
      { status: timeout ? 504 : 503 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as DELETE };
