import { useEffect, useRef, useState } from "react";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { EvidenceView, Highlight } from "../evidence";
import { reviewNames } from "../evidence";
import ErrorMessage from "./ErrorMessage";
GlobalWorkerOptions.workerSrc = workerUrl;

export default function PdfViewer({
  id,
  page,
  onPage,
  originalUrl,
  evidence,
}: {
  id: string;
  page: number;
  onPage: (page: number) => void;
  originalUrl?: string;
  evidence?: {
    geometry: EvidenceView["page_geometry"];
    highlights: Highlight[];
    selected: string;
    onSelect: (id: string) => void;
  };
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [geometryValid, setGeometryValid] = useState(false);
  const [rendered, setRendered] = useState(false);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState("");
  useEffect(() => {
    setError("");
    setPdf(null);
    const task = getDocument({
      url: originalUrl ?? `/api/v1/documents/${id}/original`,
      withCredentials: true,
      enableXfa: false,
      cMapUrl: "/pdfjs/cmaps/",
      cMapPacked: true,
      standardFontDataUrl: "/pdfjs/standard_fonts/",
      wasmUrl: "/pdfjs/wasm/",
    });
    let alive = true;
    task.promise
      .then((doc) => {
        if (alive) setPdf(doc);
      })
      .catch((e) => {
        if (alive) setError((e as Error).message);
      });
    return () => {
      alive = false;
      void task.destroy();
    };
  }, [id, originalUrl]);
  useEffect(() => {
    let render: RenderTask | undefined;
    let active = true;
    setRendered(false);
    setGeometryValid(false);
    if (!pdf || !canvas.current) return;
    void pdf
      .getPage(page)
      .then((p) => {
        if (!active || !canvas.current) return;
        const g = evidence?.geometry;
        setGeometryValid(
          Boolean(
            g &&
              g.rotation === 0 &&
              p.rotate === 0 &&
              p.view.every(
                (v, i) => Math.abs(v - [0, 0, g.width, g.height][i]) < 0.1,
              ) &&
              g.bbox.every(
                (v, i) => Math.abs(v - [0, 0, g.width, g.height][i]) < 0.1,
              ),
          ),
        );
        const viewport = p.getViewport({ scale: zoom * 1.2 });
        const target = canvas.current;
        target.width = viewport.width;
        target.height = viewport.height;
        render = p.render({ canvas: target, viewport });
        return render.promise.then(() => {
          if (active) setRendered(true);
        });
      })
      .catch((e) => {
        if (active && (e as Error).name !== "RenderingCancelledException")
          setError((e as Error).message);
      });
    return () => {
      active = false;
      render?.cancel();
    };
  }, [pdf, page, zoom, evidence?.geometry]);
  return (
    <div className="panel pdf-view">
      <div className="viewer-tools">
        <button
          className="secondary"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          Página anterior
        </button>
        <span>
          Página {page} de {pdf?.numPages ?? "…"}
        </span>
        <button
          className="secondary"
          disabled={!pdf || page >= pdf.numPages}
          onClick={() => onPage(page + 1)}
        >
          Página siguiente
        </button>
        <label>
          Zoom
          <select
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          >
            <option value={0.75}>75 %</option>
            <option value={1}>100 %</option>
            <option value={1.5}>150 %</option>
            <option value={2}>200 %</option>
          </select>
        </label>
      </div>
      <ErrorMessage message={error} />
      {!pdf && !error && <p role="status">Abriendo PDF original…</p>}
      {evidence && !geometryValid && rendered && (
        <p className="small" role="status">
          Geometría PDF no compatible (rotación, recorte o referencia no
          verificada). Consulta el resaltado en el texto original extraído.
        </p>
      )}
      {evidence &&
        geometryValid &&
        rendered &&
        evidence.highlights.some((h) => !h.boxes) && (
          <p className="small" role="status">
            Hay caracteres sin coordenadas fiables; su coincidencia se muestra
            en el texto extraído.
          </p>
        )}
      <div className="pdf-scroll">
        <div className="pdf-sheet">
          <canvas
            ref={canvas}
            aria-label={`Página ${page} del PDF original. El texto extraído accesible aparece debajo.`}
          />
          {evidence && rendered && geometryValid && evidence.geometry && (
            <svg
              className="pdf-highlights"
              viewBox={`0 0 ${evidence.geometry.width} ${evidence.geometry.height}`}
              aria-label="Resaltados del PDF"
            >
              {evidence.highlights.flatMap((h) =>
                (h.boxes ?? []).map((b, i) => (
                  <rect
                    key={`${h.finding_id}-${i}`}
                    className={`pdf-match ${h.review_state} ${h.finding_id === evidence.selected ? "selected" : ""}`}
                    x={b[0]}
                    y={b[1]}
                    width={b[2] - b[0]}
                    height={b[3] - b[1]}
                    data-finding-id={h.finding_id}
                    onClick={() => evidence.onSelect(h.finding_id)}
                  >
                    <title>
                      {reviewNames[h.review_state]} · coincidencia textual
                    </title>
                  </rect>
                )),
              )}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}
