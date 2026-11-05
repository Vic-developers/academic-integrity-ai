import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { warningLabel } from "../documents";
import type { AuditRecord, EvidenceRange, LiteralFinding } from "../audits";
import { auditStateNames, auditLimitations } from "../audits";
import { reviewNames } from "../evidence";
import ErrorMessage from "../components/ErrorMessage";
function Ranges({ ranges }: { ranges: EvidenceRange[] }) {
  return (
    <>
      {ranges.map((r, i) => (
        <div className="evidence-range" key={`${r.fragment_id}-${i}`}>
          <span className="eyebrow">
            {r.page ? `PÁGINA ${r.page} · ` : ""}PÁRRAFO {r.paragraph}
          </span>
          <blockquote>{r.text}</blockquote>
          {r.text_truncated && (
            <p className="small">
              Extracto abreviado; consulta el original para el rango completo.
            </p>
          )}
          <small className="muted">
            Posiciones originales {r.original_start}–{r.original_end} · puntos
            de código Unicode
          </small>
        </div>
      ))}
    </>
  );
}
export default function AuditResult() {
  const { id } = useParams();
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const auditQuery = useQuery({
    queryKey: ["audit", id],
    queryFn: () => api<AuditRecord>(`/audits/${id}`),
    refetchInterval: (q) =>
      q.state.data && ["pending", "running"].includes(q.state.data.state)
        ? 1500
        : false,
  });
  const audit = auditQuery.data;
  const ready = audit && ["completed", "partial"].includes(audit.state);
  const findings = useQuery({
    queryKey: ["findings", id, offset, audit?.state],
    queryFn: () =>
      api<{ items: LiteralFinding[] }>(
        `/audits/${id}/findings?limit=25&offset=${offset}`,
      ),
    enabled: Boolean(ready),
  });
  if (auditQuery.error)
    return <ErrorMessage message={auditQuery.error.message} />;
  if (!audit) return <p role="status">Cargando comparación…</p>;
  return (
    <section>
      <Link to="/auditorias">← Comparaciones</Link>
      <div className="document-heading">
        <div>
          <h1>Resultado de comparación</h1>
          <p>{audit.target.name}</p>
          <span
            className={`doc-state ${audit.state === "partial" ? "partial" : audit.state === "failed" ? "failed" : ""}`}
          >
            {auditStateNames[audit.state]}
          </span>
        </div>
        <Link
          className="button-link"
          to={`/documentos/${audit.target.document_id}`}
        >
          Consultar documento principal
        </Link>
      </div>
      <ErrorMessage message={error} />
      <div className="notice panel">
        <strong>Una coincidencia no demuestra plagio.</strong>
        <p>
          El motor verifica secuencias textuales normalizadas. La citación, el
          contexto y la decisión académica requieren revisión humana.
        </p>
        {audit.error_code && (
          <p>{auditLimitations[audit.error_code] ?? audit.error_code}</p>
        )}
        {audit.coverage.local?.extraction_partial && (
          <p>
            Hay documentos con extracción parcial; las páginas sin texto no se
            compararon.
          </p>
        )}
      </div>
      {["pending", "running"].includes(audit.state) && (
        <>
          <p role="status">
            Comparación pendiente o en curso. El progreso refleja trabajos
            reales; los hallazgos aparecerán al terminar.
          </p>
          <button
            className="secondary"
            onClick={async () => {
              try {
                await api(`/audits/${id}/cancel`, {});
                await auditQuery.refetch();
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Cancelar comparación
          </button>
        </>
      )}
      {ready && (
        <>
          <div className="cards">
            <div className="panel">
              <span className="eyebrow">
                PALABRAS CON COINCIDENCIA VERIFICADA
              </span>
              <strong className="metric">
                {audit.summary.matched_words ?? 0}{" "}
                <small>de {audit.summary.target_words ?? 0}</small>
              </strong>
              <p className="small muted">
                Sobre el texto extraído. Se cuenta una sola vez cada palabra,
                aunque aparezca en varias fuentes. No es una probabilidad de
                plagio.
              </p>
            </div>
            <div className="panel">
              <h2>Cobertura de fuentes</h2>
              <p>
                Institucionales comparadas por completo:{" "}
                {audit.coverage.local?.sources_compared ?? 0} de{" "}
                {audit.coverage.local?.sources_selected ?? 0} seleccionadas.
              </p>
              <p>
                Web:{" "}
                {audit.coverage.web?.state === "not_requested"
                  ? "no solicitada"
                  : audit.coverage.web?.state === "unavailable"
                    ? "no disponible"
                    : audit.coverage.web?.state}
              </p>
              {audit.coverage.web?.requested && (
                <p className="small">
                  {audit.coverage.web.reason}. Consultas enviadas:{" "}
                  {audit.coverage.web.queries_sent}. Fuentes web verificadas:{" "}
                  {audit.coverage.web.sources_verified}.
                </p>
              )}
            </div>
          </div>
          <Link className="button-link" to={`/auditorias/${id}/evidencias`}>
            Abrir visor de evidencias
          </Link>
          <h2>Evidencias de coincidencia literal</h2>
          <ErrorMessage message={findings.error?.message ?? ""} />
          {findings.isPending && <p role="status">Cargando evidencias…</p>}
          {findings.data?.items.map((f) => {
            const source = audit.sources.find((s) => s.id === f.source_id);
            return (
              <article className="panel finding-card" key={f.id}>
                <div className="viewer-tools">
                  <span className="pill literal">
                    Coincidencia literal normalizada
                  </span>
                  <span className="small muted">
                    {reviewNames[f.review_state]} · {f.word_count} palabras
                  </span>
                </div>
                <p>{f.evidence.explanation}</p>
                <div className="evidence-grid">
                  <div>
                    <h3>Documento principal</h3>
                    <Ranges ranges={f.evidence.target_ranges} />
                  </div>
                  <div>
                    <h3>Fuente institucional: {source?.name}</h3>
                    <Ranges ranges={f.evidence.source_ranges} />
                    {source && (
                      <Link to={`/documentos/${source.document_id}`}>
                        Consultar fuente original
                      </Link>
                    )}
                  </div>
                </div>
                <p className="small muted">
                  Citación:{" "}
                  {f.review_log.at(-1)?.citation === "correct"
                    ? "correcta"
                    : f.review_log.at(-1)?.citation === "absent"
                      ? "ausente"
                      : f.review_log.at(-1)?.citation === "incomplete"
                        ? "incompleta"
                        : "pendiente de comprobación"}
                  .{" "}
                  {f.evidence.raw_equal === true
                    ? "Los fragmentos extraídos son idénticos."
                    : "La igualdad se verificó tras normalizar Unicode, mayúsculas y separación de tokens."}
                </p>
              </article>
            );
          })}
          {findings.data?.items.length === 0 && (
            <div className="panel">
              <p>
                {audit.state === "completed"
                  ? `No se encontraron secuencias de al menos ${audit.config.min_words} palabras en las fuentes seleccionadas.`
                  : "No hay evidencias que mostrar con esta cobertura. Revisa las limitaciones antes de interpretar el resultado."}
              </p>
            </div>
          )}
          <div className="pagination">
            <button
              className="secondary"
              disabled={!offset}
              onClick={() => setOffset((v) => Math.max(0, v - 25))}
            >
              Evidencias anteriores
            </button>
            <button
              className="secondary"
              disabled={findings.data?.items.length !== 25}
              onClick={() => setOffset((v) => v + 25)}
            >
              Evidencias siguientes
            </button>
          </div>
        </>
      )}
      <details className="panel">
        <summary>Fuentes y trazabilidad</summary>
        <p>
          Motor: {audit.engine_version}. Parámetros y versiones permanecen
          ligados a esta ejecución.
        </p>
        {audit.sources.map((s) => (
          <div className="source-record" key={s.id}>
            <strong>{s.name}</strong>
            <p className="small">
              {s.state === "compared"
                ? "Contenido institucional comparado"
                : s.state === "partial"
                  ? "Comparación parcial"
                  : s.state === "skipped"
                    ? "Fuente no comparada"
                    : "Pendiente de comparación"}
              {s.reason ? ` · ${auditLimitations[s.reason] ?? s.reason}` : ""}
            </p>
            {s.extraction_warnings.map((w) => (
              <p className="small muted" key={w}>
                {warningLabel(w)}
              </p>
            ))}
            <p className="hash small">SHA-256 del original: {s.sha256}</p>
            {s.consulted_at && (
              <p className="small muted">
                Consulta del contenido:{" "}
                {new Date(s.consulted_at).toLocaleString("es")}
              </p>
            )}
          </div>
        ))}
      </details>
    </section>
  );
}
