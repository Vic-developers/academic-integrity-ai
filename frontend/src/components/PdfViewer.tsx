import { useEffect, useRef, useState } from "react";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import ErrorMessage from "./ErrorMessage";
GlobalWorkerOptions.workerSrc = workerUrl;

export default function PdfViewer({
  id,
  page,
  onPage,
}: {
  id: string;
  page: number;
  onPage: (page: number) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState("");
  useEffect(() => {
    setError("");
    const task = getDocument({
      url: `/api/v1/documents/${id}/original`,
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
  }, [id]);
  useEffect(() => {
    let render: RenderTask | undefined;
    let active = true;
    if (!pdf || !canvas.current) return;
    void pdf
      .getPage(page)
      .then((p) => {
        if (!active || !canvas.current) return;
        const viewport = p.getViewport({ scale: zoom * 1.2 });
        const target = canvas.current;
        target.width = viewport.width;
        target.height = viewport.height;
        render = p.render({ canvas: target, viewport });
        return render.promise;
      })
      .catch((e) => {
        if (active && (e as Error).name !== "RenderingCancelledException")
          setError((e as Error).message);
      });
    return () => {
      active = false;
      render?.cancel();
    };
  }, [pdf, page, zoom]);
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
      <div className="pdf-scroll">
        <canvas
          ref={canvas}
          aria-label={`Página ${page} del PDF original. El texto extraído accesible aparece debajo.`}
        />
      </div>
    </div>
  );
}
