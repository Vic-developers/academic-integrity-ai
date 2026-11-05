export type DocumentRecord = {
  can_manage?: boolean;
  id: string;
  version_id: string;
  name: string;
  state:
    | "received"
    | "extracting"
    | "completed"
    | "partial"
    | "failed"
    | "cancelled";
  format: "pdf" | "docx" | "txt";
  size: number;
  sha256: string;
  pages: number | null;
  warnings: string[];
  metadata: Record<string, unknown>;
  error: string | null;
  created_at: string;
  owner_id: string;
  assignment_id: string | null;
};
export type Assignment = {
  can_manage?: boolean;
  id: string;
  name: string;
  course: string;
  course_id: string;
};
export const stateNames: Record<DocumentRecord["state"], string> = {
  received: "Recibido",
  extracting: "Extrayendo",
  completed: "Extracción completada",
  partial: "Extracción parcial",
  failed: "Fallido",
  cancelled: "Cancelado",
};
export function warningLabel(value: string) {
  if (/page_\d+_no_text_ocr_unavailable/.test(value))
    return `Página ${value.split("_")[1]} sin texto extraíble. OCR no disponible.`;
  return (
    (
      {
        txt_pages_are_form_feed_sections:
          "Las páginas del TXT corresponden a separadores de página del archivo.",
        docx_structured_view_not_word_pagination:
          "Vista estructurada de DOCX. La paginación de Word no está disponible.",
        pdf_reading_order_and_line_paragraphs_require_review:
          "Los párrafos de PDF corresponden a líneas. El orden de lectura requiere revisión en diseños complejos.",
      } as Record<string, string>
    )[value] ?? value
  );
}
