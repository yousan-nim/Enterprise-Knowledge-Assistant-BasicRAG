export type DocumentInfo = {
  document_id: string;
  source: string;
  embedding_model: string;
  chunks: number;
};
export type Source = {
  id: string;
  text: string;
  source: string;
  page: number;
  extraction_method: "direct" | "ocr";
  score: number;
};
export type Answer = {
  answer: string;
  citation_ids: string[];
  found: boolean;
  sources: Source[];
};
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    cache: "no-store",
  });
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      /* A non-JSON gateway error still gets a readable message. */
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function validateFile(file: File): string | null {
  if (!/\.(pdf|txt|md)$/i.test(file.name))
    return "Choose a PDF, TXT or Markdown file.";
  if (file.size > 1024 * 1024)
    return "Your file is too large. Please choose a file under 1 MiB.";
  if (file.size === 0) return "This file is empty. Please choose another file.";
  return null;
}
