import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { queryClient } from "../query";
import type { DocumentRecord } from "../documents";
import { stateNames, warningLabel } from "../documents";
import ErrorMessage from "../components/ErrorMessage";
const PdfViewer = lazy(() => import("../components/PdfViewer"));

type Fragment = {
  id: string;
  original: string;
  normalized: string;
  page: number | null;
  paragraph: number;
  section: string | null;
};
export default function DocumentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  useEffect(() => {
    setPage(1);
    setOffset(0);
  }, [id]);
  const [page, setPage] = useState(1);
  const [offset, setOffset] = useState(0);
  const [normalized, setNormalized] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const doc = useQuery({
    queryKey: ["document", id],
    queryFn: () => api<DocumentRecord>(`/documents/${id}`),
    refetchInterval: (q) =>
      q.state.data && ["received", "extracting"].includes(q.state.data.state)
        ? 1500
        : false,
  });
  const document = doc.data;
  const ready = document && ["completed", "partial"].includes(document.state);
  const fragments = useQuery({
    queryKey: ["fragments", id, page, offset, document?.state],
    queryFn: () =>
      api<{ items: Fragment[] }>(
        `/documents/${id}/fragments?limit=100&offset=${offset}${document?.format === "pdf" ? `&page=${page}` : ""}`,
      ),
    enabled: Boolean(ready),
  });
  async function action(kind: "cancel" | "delete") {
    if (
      kind === "delete" &&
      !window.confirm(
        "¿Eliminar este documento y programar la eliminación de su original privado?",
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await api(
        `/documents/${id}${kind === "cancel" ? "/cancel" : ""}`,
        {},
        kind === "delete" ? "DELETE" : "POST",
      );
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (kind === "delete") navigate("/documentos");
      else await doc.refetch();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (doc.isPending) return <p role="status">Cargando documento…</p>;
  if (!document)
    return (
      <ErrorMessage message={doc.error?.message ?? "Documento no disponible"} />
    );
  return (
    <section>
      <Link to="/documentos">← Documentos</Link>
      <div className="document-heading">
        <div>
          <h1>{document.name}</h1>
          <span className={`doc-state ${document.state}`}>
            {stateNames[document.state]}
          </span>
        </div>
        <a className="button-link" href={`/api/v1/documents/${id}/original`}>
          Descargar original
        </a>
      </div>
      <ErrorMessage message={error || document.error || ""} />
      <div className="document-facts">
        <span>
          {document.format.toUpperCase()} · {(document.size / 1024).toFixed(1)}{" "}
          KiB
        </span>
        <span>
          {document.pages === null
            ? document.format === "docx"
              ? "Sin paginación de Word"
              : "Paginación pendiente"
            : `${document.pages} página(s) extraídas`}
        </span>
      </div>
      <div className="notice panel">
        <strong>Alcance: extracción documental</strong>
        <p>
          El texto aún no se ha comparado con otras fuentes. Este estado no
          representa una auditoría de integridad.
        </p>
        {document.warnings.map((w) => (
          <p key={w}>{warningLabel(w)}</p>
        ))}
      </div>
      {document.format === "pdf" && ready && (
        <Suspense fallback={<p role="status">Cargando visor PDF…</p>}>
          <PdfViewer
            key={document.id}
            id={document.id}
            page={page}
            onPage={(p) => {
              setPage(p);
              setOffset(0);
            }}
          />
        </Suspense>
      )}
      {ready && (
        <div className="panel">
          <div className="viewer-tools">
            <h2>Texto extraído</h2>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={normalized}
                onChange={(e) => setNormalized(e.target.checked)}
              />
              Ver normalizado
            </label>
          </div>
          <ErrorMessage message={fragments.error?.message ?? ""} />
          {fragments.isPending && <p role="status">Cargando texto…</p>}
          {fragments.data?.items.map((f) => (
            <article className="document-paragraph" key={f.id}>
              <span className="eyebrow">
                {f.page ? `PÁGINA ${f.page} · ` : ""}PÁRRAFO {f.paragraph}
                {f.section ? ` · ${f.section}` : ""}
              </span>
              <p>{normalized ? f.normalized : f.original}</p>
            </article>
          ))}
          {fragments.data?.items.length === 0 && (
            <p>
              No hay texto extraíble en esta página. Consulta las limitaciones
              indicadas.
            </p>
          )}
          <div className="pagination">
            <button
              className="secondary"
              disabled={!offset}
              onClick={() => setOffset((v) => Math.max(0, v - 100))}
            >
              Texto anterior
            </button>
            <button
              className="secondary"
              disabled={fragments.data?.items.length !== 100}
              onClick={() => setOffset((v) => v + 100)}
            >
              Texto siguiente
            </button>
          </div>
        </div>
      )}
      <details className="panel">
        <summary>Propiedades e integridad del archivo</summary>
        <p className="small">
          Los metadatos son información contextual; no demuestran autoría.
        </p>
        <dl>
          <dt>SHA-256 del original</dt>
          <dd className="hash">{document.sha256}</dd>
          {Object.entries(document.metadata)
            .filter(([key]) => key !== "pages")
            .map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
        </dl>
      </details>
      <div className="viewer-tools">
        {ready && (
          <Link
            className="button-link"
            to={`/auditorias?document=${document.id}`}
          >
            Comparar con fuentes autorizadas
          </Link>
        )}
        {document.can_manage &&
          ["received", "extracting"].includes(document.state) && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => void action("cancel")}
            >
              Cancelar procesamiento
            </button>
          )}
        {document.can_manage && (
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void action("delete")}
          >
            Eliminar documento
          </button>
        )}
      </div>
    </section>
  );
}
