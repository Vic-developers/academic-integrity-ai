import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { BiblioReference, BiblioRun, BiblioSpan } from "../bibliography";
import { biblioStates, biblioLimitations, biblioFields } from "../bibliography";
import ErrorMessage from "../components/ErrorMessage";
function Spans({ spans }: { spans: BiblioSpan[] }) {
  return (
    <>
      {spans.map((s, i) => (
        <div key={i} className="evidence-range">
          <span className="eyebrow">
            {s.page ? `Página ${s.page} · ` : ""}Párrafo {s.paragraph} ·
            Posiciones {s.original_start}–{s.original_end}
          </span>
          <blockquote>{s.text}</blockquote>
          {s.text_truncated && (
            <small>Extracto abreviado; consulta la versión original.</small>
          )}
          <details>
            <summary>Integridad del pasaje</summary>
            <p className="hash small">SHA-256: {s.span_sha256}</p>
          </details>
        </div>
      ))}
    </>
  );
}
export default function BibliographyResult() {
  const { id } = useParams();
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const query = useQuery({
    queryKey: ["bibliography", id],
    queryFn: () => api<BiblioRun>(`/bibliography/${id}`),
    refetchInterval: (q) =>
      q.state.data && ["pending", "running"].includes(q.state.data.state)
        ? 1500
        : 10000,
    gcTime: 0,
  });
  const run = query.data;
  const ready = run && ["completed", "partial"].includes(run.state);
  const refs = useQuery({
    queryKey: ["bibliography-references", id, offset, run?.state],
    queryFn: () =>
      api<{ items: BiblioReference[] }>(
        `/bibliography/${id}/references?limit=25&offset=${offset}`,
      ),
    enabled: Boolean(ready),
    refetchInterval: 10000,
    gcTime: 0,
  });
  const detail = useQuery({
    queryKey: ["bibliography-response", id, selected],
    queryFn: () =>
      api<{ provider_responses: unknown[] }>(
        `/bibliography/${id}/references/${selected}`,
      ),
    enabled: selected !== null && Boolean(ready),
    gcTime: 0,
  });
  if (query.error || refs.error || detail.error)
    return (
      <ErrorMessage
        message={(query.error || refs.error || detail.error)!.message}
      />
    );
  if (!run) return <p role="status">Cargando revisión bibliográfica…</p>;
  return (
    <section>
      <Link to="/bibliografia">← Bibliografía</Link>
      <h1>Resultado bibliográfico</h1>
      <p>{run.target.name}</p>
      <span className={`doc-state ${run.state === "partial" ? "partial" : ""}`}>
        {biblioStates[run.state] ?? run.state}
      </span>
      <div className="notice panel">
        <strong>
          Los metadatos no validan una afirmación ni demuestran plagio.
        </strong>
        <p>
          La extracción y los patrones de cita son candidatos para revisión
          humana. No localizar un DOI en un proveedor no demuestra que la fuente
          sea inventada.
        </p>
        {!run.config.request_external && (
          <p>
            No se solicitó consulta externa: ninguna fuente se presenta como
            verificada en línea.
          </p>
        )}
      </div>
      <ErrorMessage message={error || run.error_code || ""} />
      {["pending", "running"].includes(run.state) && (
        <>
          <p role="status">Extrayendo y revisando referencias…</p>
          <button
            className="secondary"
            onClick={async () => {
              try {
                await api(`/bibliography/${id}/cancel`, {});
                await query.refetch();
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Cancelar revisión
          </button>
        </>
      )}
      {ready && (
        <>
          <div className="cards">
            <div className="panel">
              <span className="eyebrow">REFERENCIAS CANDIDATAS</span>
              <strong className="metric">{run.summary.references ?? 0}</strong>
              <p>
                Duplicados candidatos: {run.summary.duplicate_candidates ?? 0}
              </p>
            </div>
            <div className="panel">
              <h2>Cobertura externa</h2>
              <p>
                Referencias con metadatos recuperados:{" "}
                {run.summary.metadata_retrieved_references ?? 0}
              </p>
              <p>Intentos de consulta: {run.summary.provider_attempts ?? 0}</p>
            </div>
          </div>
          <details className="panel">
            <summary>Alcance y limitaciones</summary>
            {run.limitations.map((l) => (
              <p key={l}>{biblioLimitations[l] ?? l}</p>
            ))}
            <p>
              Citas sin correspondencia en patrones compatibles:{" "}
              {run.summary.unmatched_citation_candidates ?? 0}
            </p>
            <p>
              Referencias sin cita reconocida:{" "}
              {run.summary.uncited_reference_candidates ?? 0}
            </p>
            <p className="hash">
              SHA-256 del documento original: {run.target.sha256}
            </p>
          </details>
          <h2>Referencias extraídas</h2>
          {refs.data?.items.map((r) => (
            <article className="panel bibliography-reference" key={r.ordinal}>
              <h3>Referencia {r.ordinal}</h3>
              <span className="pill">
                {biblioStates[r.verification_state] ?? r.verification_state}
              </span>
              <Spans spans={r.spans} />
              {r.duplicate_of && (
                <p>
                  Posible duplicado de la referencia {r.duplicate_of}; requiere
                  revisión.
                </p>
              )}
              <p>
                Citación local:{" "}
                {r.citation_state === "seen_in_supported_pattern"
                  ? "Encontrada mediante un patrón compatible"
                  : r.citation_state === "not_assessed"
                    ? "No evaluada sin apartado bibliográfico"
                    : "No se reconoció una cita; revisar manualmente"}
                .
              </p>
              {r.fields.missing_fields.length > 0 && (
                <p className="small">
                  Campos que no se pudieron extraer:{" "}
                  {r.fields.missing_fields
                    .map((f) => biblioFields[f] ?? f)
                    .join(", ")}
                  . Esto no prueba que falten en el documento.
                </p>
              )}
              {r.fields.dois.map((doi) => (
                <p key={doi}>
                  DOI candidato:{" "}
                  <a
                    href={`https://doi.org/${encodeURIComponent(doi)}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {doi}
                  </a>
                </p>
              ))}
              {r.lookups.map((lookup) => (
                <div className="source-record" key={lookup.provider}>
                  <strong>
                    {lookup.provider === "crossref" ? "Crossref" : "OpenAlex"}:{" "}
                    {biblioStates[lookup.state] ?? lookup.state}
                  </strong>
                  {lookup.retrieved_at && (
                    <p>
                      Consulta:{" "}
                      {new Date(lookup.retrieved_at).toLocaleString("es")}
                    </p>
                  )}
                  {lookup.response_sha256 && (
                    <p className="hash small">
                      SHA-256 de respuesta: {lookup.response_sha256}
                    </p>
                  )}
                  {lookup.comparison && (
                    <>
                      <p>{biblioStates[lookup.comparison.state]}</p>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Campo</th>
                              <th>En referencia</th>
                              <th>En proveedor</th>
                              <th>Comparación</th>
                            </tr>
                          </thead>
                          <tbody>
                            {lookup.comparison.checks.map((c) => (
                              <tr key={c.field}>
                                <td>{biblioFields[c.field] ?? c.field}</td>
                                <td>{JSON.stringify(c.printed)}</td>
                                <td>{JSON.stringify(c.observed)}</td>
                                <td>
                                  {c.state === "partial_equal"
                                    ? "Coincide el primer autor; lista completa no comparada"
                                    : c.state === "equal"
                                      ? "Coincide"
                                      : c.state === "different"
                                        ? "Diferente: revisar"
                                        : "No comparado"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              ))}
              {r.lookups.some((l) => l.response_sha256) && (
                <button
                  className="secondary"
                  onClick={() => setSelected(r.ordinal)}
                >
                  Ver respuesta registrada de referencia {r.ordinal}
                </button>
              )}
            </article>
          ))}
          {refs.data?.items.length === 0 && (
            <p>No se identificaron referencias en este alcance.</p>
          )}
          <div className="pagination">
            <button
              className="secondary"
              disabled={!offset}
              onClick={() => setOffset((v) => Math.max(0, v - 25))}
            >
              Referencias anteriores
            </button>
            <button
              className="secondary"
              disabled={refs.data?.items.length !== 25}
              onClick={() => setOffset((v) => v + 25)}
            >
              Referencias siguientes
            </button>
          </div>
          {selected !== null && (
            <details open className="panel">
              <summary>Respuesta registrada de referencia {selected}</summary>
              <pre className="provider-json">
                {JSON.stringify(detail.data?.provider_responses ?? [], null, 2)}
              </pre>
              <button className="secondary" onClick={() => setSelected(null)}>
                Cerrar respuesta
              </button>
            </details>
          )}
          <details className="panel">
            <summary>
              Candidatos de citas en el texto ({run.citations.length})
            </summary>
            {run.citations.map((c, i) => (
              <article key={i}>
                <p>
                  {c.label} ·{" "}
                  {c.state === "matched"
                    ? "Correspondencia local"
                    : c.state === "ambiguous"
                      ? "Correspondencia ambigua"
                      : "Sin referencia reconocida: revisar"}
                </p>
                <Spans spans={c.spans} />
              </article>
            ))}
          </details>
          <a className="button-link" href={`/api/v1/bibliography/${id}/export`}>
            Exportar evidencia bibliográfica JSON
          </a>
          <p>
            <Link to={`/documentos/${run.target.document_id}`}>
              Consultar documento original
            </Link>
          </p>
        </>
      )}
    </section>
  );
}
