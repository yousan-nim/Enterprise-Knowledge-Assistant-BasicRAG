# Folio — knowledge workspace

Responsive glass UI for the Enterprise Knowledge Assistant. Document Q&A uses the real RAG API;
Free chat calls the chat endpoint without document retrieval. No answers are prefilled or fabricated.

## Run the whole stack

From the repository root, with Docker Desktop running:

- Mac/Linux: `sh scripts/dev.sh`
- Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1`

Open http://localhost:3000. The first run downloads models. Configure `WEB_PORT` in the root `.env`
if port 3000 is already in use. The Swagger API remains at http://localhost:8080/docs.

## Develop only the frontend

Requires Node.js 22+ and the backend already running:

```bash
cd frontend
npm ci
npm run dev
```

`BACKEND_URL` defaults to `http://127.0.0.1:8080`. Copy `.env.example` to `.env.local` to change it.
Docker sets it to `http://backend:8000`. This is a server-side runtime setting, not a public browser key.

The browser calls `/api/v1/...` on its own origin. A narrowly scoped Next.js route handler forwards
GET/POST/DELETE to the backend, preserving multipart boundaries and backend error/status codes.
It restricts proxy paths and request bodies to 2 MiB, allowing multipart overhead around the API's
1 MiB file limit. The backend remains responsible for document parsing and validation. No CORS changes
are needed. HTTP and timeout failures are shown in the UI, without invented answers or progress percentages.

## UI behavior

- Drag/drop or choose a PDF, TXT or Markdown document. A sample handbook uses the same real upload API.
- Replacing or deleting the indexed document requires confirmation. The current backend stores one document.
- Sources display original text, source filename, page, OCR/direct provenance, and cosine similarity.
  Similarity is labeled as a retrieval score, not confidence; cited and retrieved-only passages are distinguished.
- Earlier messages are displayed but not sent as model context: each question is answered independently.
- Conversation history is in memory for this tab only. It is cleared on reload, successful document changes,
  or switching chat modes. Documents persist in PostgreSQL.
- Light glass styling includes solid fallbacks, keyboard focus, reduced motion, accessible labels,
  English/Thai text, and responsive layouts from mobile to wide desktop.
- This is a local portfolio demo with no authentication; do not publish it unchanged on the open internet.

## Verify

```bash
npm run format:check
npm run build
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

On macOS, an installed Chrome can be used without downloading Chromium:

```bash
PLAYWRIGHT_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

Browser tests cover upload/ask/citations/delete, replacement failure preservation, file validation,
free chat, missing answers, API failures, keyboard behavior, responsive widths, WCAG A/AA checks,
and the server-side multipart proxy. Model responses are stubbed in automated browser tests.
Tests use port 3100 (override `FRONTEND_TEST_PORT`) and a local fake upstream on port 18081.
Do not run a second Next dev server from this same directory while testing (Next dev uses a directory lock).

Design: warm paper, forest-green ink and translucent surfaces; no runtime component library.
Fonts are loaded from Google Fonts with local/system fallbacks, so builds do not depend on font downloads.
