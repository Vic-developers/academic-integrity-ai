import type { AuditSnapshot, EvidenceRange } from "./audits";
export type ReviewState =
  | "pending"
  | "reviewed"
  | "justified"
  | "dismissed"
  | "confirmed";
export const reviewNames: Record<ReviewState, string> = {
  pending: "Pendiente",
  reviewed: "Revisado",
  justified: "Justificado",
  dismissed: "Descartado",
  confirmed: "Coincidencia confirmada",
};
export type ReviewEvent = {
  revision: number;
  state: ReviewState;
  citation: string;
  reason: string;
  actor_id: string;
  at: string;
};
export type Highlight = {
  finding_id: string;
  start: number;
  end: number;
  review_state: ReviewState;
  boxes: number[][] | null;
};
export type EvidenceView = {
  document: AuditSnapshot & { format: string; author?: string | null };
  fragment: {
    id: string;
    original: string;
    sha256: string;
    page: number | null;
    paragraph: number;
    section: string | null;
    sentences: { start: number; end: number }[];
  };
  range_index: number;
  range_count: number;
  selected_range: EvidenceRange & { sentences: number[] };
  highlights: Highlight[];
  page_geometry: {
    number: number;
    width: number;
    height: number;
    rotation: number;
    bbox: number[];
  } | null;
};
export async function sha256(text: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)),
    ),
    (v) => v.toString(16).padStart(2, "0"),
  ).join("");
}
export async function verifyView(view: EvidenceView): Promise<EvidenceView> {
  const chars = Array.from(view.fragment.original);
  const span = view.selected_range;
  if (
    !(
      span.original_start >= 0 &&
      span.original_start < span.original_end &&
      span.original_end <= chars.length
    ) ||
    (await sha256(view.fragment.original)) !== view.fragment.sha256 ||
    (await sha256(
      chars.slice(span.original_start, span.original_end).join(""),
    )) !== span.span_sha256 ||
    view.highlights.some(
      (h) => h.start < 0 || h.start >= h.end || h.end > chars.length,
    )
  )
    throw new Error(
      "No se pudo verificar el mapa de posiciones; se ha ocultado el resaltado.",
    );
  return view;
}
// Split on all boundaries so overlapping findings never nest or shift offsets.
export function segments(text: string, highlights: Highlight[]) {
  const chars = Array.from(text);
  const boundaries = [
    ...new Set([
      0,
      chars.length,
      ...highlights.flatMap((h) => [h.start, h.end]),
    ]),
  ].sort((a, b) => a - b);
  return boundaries
    .slice(0, -1)
    .map((start, i) => ({
      start,
      text: chars.slice(start, boundaries[i + 1]).join(""),
      highlights: highlights.filter(
        (h) => h.start < boundaries[i + 1] && h.end > start,
      ),
    }));
}
