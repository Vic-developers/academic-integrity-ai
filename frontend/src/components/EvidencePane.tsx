import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { EvidenceView } from "../evidence";
import { segments, verifyView, reviewNames } from "../evidence";
import ErrorMessage from "./ErrorMessage";
const PdfViewer = lazy(() => import("./PdfViewer"));
export default function EvidencePane({
  auditId,
  findingId,
  side,
  onSelect,
}: {
  auditId: string;
  findingId: string;
  side: "target" | "source";
  onSelect: (id: string) => void;
}) {
  const [index, setIndex] = useState(0);
  const [pdfPage, setPdfPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const text = useRef<HTMLParagraphElement>(null);
  const query = useQuery({
    queryKey: ["evidence-view", auditId, findingId, side, index],
    queryFn: async () =>
      verifyView(
        await api<EvidenceView>(
          `/audits/${auditId}/findings/${findingId}/view?side=${side}&range_index=${index}`,
        ),
      ),
    refetchInterval: 10000,
    gcTime: 0,
  });
  const data = query.data;
  useEffect(() => {
    setPdfPage(data?.fragment.page ?? 1);
  }, [data?.fragment.id]);
  useEffect(() => {
    text.current
      ?.querySelector('[aria-current="true"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [data?.fragment.id, findingId]);
  if (query.error) return <ErrorMessage message={query.error.message} />;
  if (!data) return <p role="status">Verificando posiciones originales…</p>;
  const originalUrl = `/api/v1/audits/${auditId}/findings/${findingId}/original?side=${side}`;
  return (
    <section
      className="panel evidence-pane"
      aria-label={
        side === "target"
          ? "Documento principal con resaltado"
          : "Fuente con resaltado"
      }
    >
      <span className="eyebrow">
        {side === "target" ? "DOCUMENTO PRINCIPAL" : "FUENTE INSTITUCIONAL"}
      </span>
      <h2>{data.document.name}</h2>
      {data.document.author && (
        <p className="small">
          Autor declarado en metadatos: {data.document.author}
        </p>
      )}
      <div className="viewer-tools">
        <button
          className="secondary"
          disabled={index === 0}
          onClick={() => setIndex((i) => i - 1)}
        >
          Fragmento anterior
        </button>
        <span>
          Fragmento {index + 1} de {data.range_count}
        </span>
        <button
          className="secondary"
          disabled={index + 1 >= data.range_count}
          onClick={() => setIndex((i) => i + 1)}
        >
          Fragmento siguiente
        </button>
      </div>
      <p className="small">
        {data.fragment.page ? `Página ${data.fragment.page} · ` : ""}Párrafo{" "}
        {data.fragment.paragraph} · Oración(es){" "}
        {data.selected_range.sentences.join(", ") || "sin referencia"} ·
        Posiciones {data.selected_range.original_start}–
        {data.selected_range.original_end}
      </p>
      {data.document.format === "pdf" && (
        <Suspense fallback={<p role="status">Abriendo PDF…</p>}>
          <PdfViewer
            key={data.fragment.id}
            id={data.document.document_id}
            originalUrl={originalUrl}
            page={pdfPage}
            onPage={setPdfPage}
            evidence={{
              geometry:
                pdfPage === data.fragment.page ? data.page_geometry : null,
              highlights: pdfPage === data.fragment.page ? data.highlights : [],
              selected: findingId,
              onSelect,
            }}
          />
        </Suspense>
      )}
      {data.document.format === "pdf" && pdfPage !== data.fragment.page && (
        <button
          className="secondary"
          onClick={() => setPdfPage(data.fragment.page ?? 1)}
        >
          Volver a la página de coincidencia
        </button>
      )}
      {data.document.format === "docx" && (
        <p className="small muted">
          Vista estructurada del DOCX: conserva el texto extraído y sus
          párrafos; no reproduce la paginación de Word.
        </p>
      )}
      <label className="text-zoom">
        Zoom del texto{" "}
        <select value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
          <option value={1}>100 %</option>
          <option value={1.25}>125 %</option>
          <option value={1.5}>150 %</option>
        </select>
      </label>
      <div className="evidence-context">
        <p
          ref={text}
          className="original-context"
          style={{ fontSize: `${zoom}em` }}
          aria-label="Texto original con contexto"
        >
          {segments(data.fragment.original, data.highlights).map((part) => {
            if (!part.highlights.length)
              return <span key={part.start}>{part.text}</span>;
            const active =
              part.highlights.find((h) => h.finding_id === findingId) ??
              part.highlights[0];
            return (
              <mark
                key={part.start}
                className={`match ${active.review_state}`}
                aria-current={
                  active.finding_id === findingId ? "true" : undefined
                }
                tabIndex={0}
                role="button"
                aria-label={`${reviewNames[active.review_state]}: ${part.text}. ${part.highlights.length} coincidencia(s)`}
                data-finding-ids={part.highlights
                  .map((h) => h.finding_id)
                  .join(",")}
                onClick={() => onSelect(active.finding_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(active.finding_id);
                  }
                }}
              >
                {part.text}
              </mark>
            );
          })}
        </p>
      </div>
      <p className="small muted">
        Texto original seleccionable. El resaltado usa puntos de código Unicode
        y hashes verificados.
      </p>
      <details>
        <summary>Versión y procedencia</summary>
        <p>
          Tipo: coincidencia textual normalizada · Contenido institucional
          verificado
        </p>
        <p>Versión: {data.document.version_id}</p>
        <p className="hash">SHA-256: {data.document.sha256}</p>
        <p>
          Consulta:{" "}
          {data.document.consulted_at
            ? new Date(data.document.consulted_at).toLocaleString("es")
            : "Registrada en la auditoría"}
        </p>
      </details>
      <a href={originalUrl}>Descargar esta versión original</a>
    </section>
  );
}
