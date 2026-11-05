import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { DocumentRecord } from "../documents";
import type { BiblioRun } from "../bibliography";
import { biblioStates } from "../bibliography";
import ErrorMessage from "../components/ErrorMessage";
export default function Bibliography() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const [external, setExternal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const docs = useQuery({
    queryKey: ["biblio-docs", offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?limit=25&offset=${offset}`),
    refetchInterval: (q) =>
      q.state.data?.items.some((d) =>
        ["received", "extracting"].includes(d.state),
      )
        ? 1500
        : false,
  });
  const doc = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api<DocumentRecord>(`/documents/${documentId}`),
    enabled: Boolean(documentId),
    refetchInterval: (q) =>
      q.state.data && ["received", "extracting"].includes(q.state.data.state)
        ? 1500
        : false,
  });
  const history = useQuery({
    queryKey: ["bibliography-history", historyOffset],
    queryFn: () =>
      api<{ items: BiblioRun[] }>(
        `/bibliography?limit=25&offset=${historyOffset}`,
      ),
  });
  const caps = useQuery({
    queryKey: ["bibliography-capabilities"],
    queryFn: () =>
      api<{ crossref_enabled: boolean; openalex_enabled: boolean }>(
        "/bibliography/capabilities",
      ),
  });
  useEffect(() => {
    setExternal(false);
    setError("");
  }, [documentId]);
  if (doc.error || docs.error || history.error || caps.error)
    return (
      <ErrorMessage
        message={
          (doc.error || docs.error || history.error || caps.error)!.message
        }
      />
    );
  const ready = doc.data && ["completed", "partial"].includes(doc.data.state);
  return (
    <section>
      <h1>Verificación bibliográfica</h1>
      <p>
        Extrae referencias y comprueba metadatos. Una referencia no localizada
        no demuestra que sea inventada.
      </p>
      <ErrorMessage message={error} />
      <div className="panel">
        <h2>{doc.data?.name ?? "Selecciona un documento"}</h2>
        {!documentId ? (
          <>
            <p>Solo se muestran documentos a los que tienes acceso.</p>
            {docs.data?.items.map((d) => (
              <p key={d.id}>
                <Link to={`/bibliografia/${d.id}`}>{d.name}</Link>
              </p>
            ))}
            <div className="pagination">
              <button
                className="secondary"
                disabled={!offset}
                onClick={() => setOffset((v) => Math.max(0, v - 25))}
              >
                Documentos anteriores
              </button>
              <button
                className="secondary"
                disabled={docs.data?.items.length !== 25}
                onClick={() => setOffset((v) => v + 25)}
              >
                Documentos siguientes
              </button>
            </div>
          </>
        ) : (
          <>
            <Link to={`/documentos/${documentId}`}>
              Consultar documento original
            </Link>
            <p>
              El análisis local busca un apartado de referencias, DOI,
              duplicados y patrones de citas APA/numéricas. Su alcance es
              limitado y se muestra en el resultado.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={external}
                disabled={
                  !caps.data?.crossref_enabled && !caps.data?.openalex_enabled
                }
                onChange={(e) => setExternal(e.target.checked)}
              />
              Autorizar consulta externa de los DOI extraídos
            </label>
            <p className="small muted">
              {caps.data?.crossref_enabled || caps.data?.openalex_enabled
                ? "Solo se envían identificadores DOI; no se envía el texto del documento. OpenAlex necesita configuración propia."
                : "Crossref y OpenAlex no están habilitados. La revisión local no verifica la existencia de las fuentes."}
            </p>
            <button
              disabled={!ready || busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const run = await api<BiblioRun>("/bibliography", {
                    document_id: documentId,
                    request_external: external,
                    providers: external
                      ? [
                          ...(caps.data?.crossref_enabled ? ["crossref"] : []),
                          ...(caps.data?.openalex_enabled ? ["openalex"] : []),
                        ]
                      : ["crossref", "openalex"],
                  });
                  navigate(`/bibliografia/resultados/${run.id}`);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Creando revisión…" : "Revisar bibliografía"}
            </button>
            {!ready && (
              <p role="status">
                Espera a que finalice la extracción del documento.
              </p>
            )}
          </>
        )}
      </div>
      <h2>Revisiones anteriores</h2>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Documento</th>
              <th>Estado</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            {history.data?.items.map((r) => (
              <tr key={r.id}>
                <td>{r.target.name}</td>
                <td>{biblioStates[r.state] ?? r.state}</td>
                <td>
                  <Link to={`/bibliografia/resultados/${r.id}`}>
                    Abrir revisión
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <button
          className="secondary"
          disabled={!historyOffset}
          onClick={() => setHistoryOffset((v) => Math.max(0, v - 25))}
        >
          Revisiones anteriores
        </button>
        <button
          className="secondary"
          disabled={history.data?.items.length !== 25}
          onClick={() => setHistoryOffset((v) => v + 25)}
        >
          Revisiones siguientes
        </button>
      </div>
    </section>
  );
}
