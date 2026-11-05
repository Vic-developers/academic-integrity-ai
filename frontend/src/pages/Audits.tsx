import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { queryClient } from "../query";
import type { DocumentRecord } from "../documents";
import type { AuditRecord } from "../audits";
import { auditStateNames } from "../audits";
import ErrorMessage from "../components/ErrorMessage";
export default function Audits() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [target, setTarget] = useState<DocumentRecord | null>(null);
  const [sources, setSources] = useState<Record<string, DocumentRecord>>({});
  const [web, setWeb] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const capabilities = useQuery({
    queryKey: ["audit-capabilities"],
    queryFn: () =>
      api<{
        min_words: number;
        max_sources: number;
        max_characters: number;
        web_available: boolean;
        web_reason: string;
      }>("/audits/capabilities"),
  });
  const documents = useQuery({
    queryKey: ["audit-documents", offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?limit=25&offset=${offset}`),
    refetchInterval: (q) =>
      q.state.data?.items.some((d) =>
        ["received", "extracting"].includes(d.state),
      )
        ? 1500
        : false,
  });
  const initial = useQuery({
    queryKey: ["initial-audit-document", params.get("document")],
    queryFn: () => api<DocumentRecord>(`/documents/${params.get("document")}`),
    enabled: Boolean(params.get("document")),
    refetchInterval: (q) =>
      q.state.data && ["received", "extracting"].includes(q.state.data.state)
        ? 1500
        : false,
  });
  useEffect(() => {
    if (initial.data)
      setTarget((old) =>
        !old || old.id === initial.data!.id ? initial.data! : old,
      );
  }, [initial.data]);
  const history = useQuery({
    queryKey: ["audits", historyOffset],
    queryFn: () =>
      api<{ items: AuditRecord[] }>(`/audits?limit=25&offset=${historyOffset}`),
    refetchInterval: (q) =>
      q.state.data?.items.some((a) => ["pending", "running"].includes(a.state))
        ? 1500
        : false,
  });
  const maximum = capabilities.data?.max_sources ?? 20;
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!target) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<AuditRecord>("/audits", {
        document_id: target.id,
        source_document_ids: Object.keys(sources),
        request_web: web,
      });
      await queryClient.invalidateQueries({ queryKey: ["audits"] });
      navigate(`/auditorias/${result.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <span className="eyebrow">EVIDENCIAS TEXTUALES</span>
      <h1>Comparación literal</h1>
      <p className="muted">
        Selecciona el documento y las fuentes institucionales que tienes permiso
        de consultar. Una coincidencia requiere revisión humana.
      </p>
      <form className="panel" onSubmit={submit}>
        <h2>Nueva comparación</h2>
        <p>
          Se buscan secuencias continuas de al menos{" "}
          {capabilities.data?.min_words ?? 8} palabras. No se detectan
          paráfrasis ni autoría de IA.
        </p>
        <p className="selection-summary">
          <strong>Principal:</strong> {target?.name ?? "Sin seleccionar"}
          <br />
          <strong>Fuentes:</strong> {Object.keys(sources).length} de {maximum}
        </p>
        <ErrorMessage
          message={
            error ||
            documents.error?.message ||
            initial.error?.message ||
            capabilities.error?.message ||
            ""
          }
        />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Principal</th>
                <th>Fuente</th>
                <th>Documento</th>
              </tr>
            </thead>
            <tbody>
              {documents.data?.items.map((d) => {
                const ready = ["completed", "partial"].includes(d.state);
                return (
                  <tr key={d.id}>
                    <td>
                      <input
                        type="radio"
                        name="principal"
                        aria-label={`Principal: ${d.name}`}
                        checked={target?.id === d.id}
                        disabled={!ready}
                        onChange={() => {
                          setTarget(d);
                          setSources((old) => {
                            const next = { ...old };
                            delete next[d.id];
                            return next;
                          });
                        }}
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Fuente: ${d.name}`}
                        checked={Boolean(sources[d.id])}
                        disabled={
                          !ready ||
                          target?.id === d.id ||
                          (!sources[d.id] &&
                            Object.keys(sources).length >= maximum)
                        }
                        onChange={(e) =>
                          setSources((old) => {
                            const next = { ...old };
                            if (e.target.checked) next[d.id] = d;
                            else delete next[d.id];
                            return next;
                          })
                        }
                      />
                    </td>
                    <td>
                      {d.name}
                      {!ready && (
                        <small className="muted">
                          {" "}
                          · Extracción aún no disponible
                        </small>
                      )}
                      {d.state === "partial" && <small> · Texto parcial</small>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {documents.data?.items.length === 0 && (
          <p>
            No hay documentos en esta página. Carga y extrae archivos en
            Documentos.
          </p>
        )}
        <div className="pagination">
          <button
            type="button"
            className="secondary"
            disabled={!offset}
            onClick={() => setOffset((v) => Math.max(0, v - 25))}
          >
            Documentos anteriores
          </button>
          <button
            type="button"
            className="secondary"
            disabled={documents.data?.items.length !== 25}
            onClick={() => setOffset((v) => v + 25)}
          >
            Documentos siguientes
          </button>
        </div>
        {Object.values(sources).length > 0 && (
          <p className="small muted">
            Fuentes seleccionadas:{" "}
            {Object.values(sources)
              .map((s) => s.name)
              .join(", ")}
          </p>
        )}
        <div className="notice">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={web}
              onChange={(e) => setWeb(e.target.checked)}
            />
            Solicitar búsqueda web
          </label>
          <p>
            {capabilities.data?.web_reason ?? "Consultando disponibilidad web…"}
            . Si se solicita sin proveedor, el resultado indicará cobertura
            parcial; no se enviarán fragmentos.
          </p>
        </div>
        <button
          disabled={
            busy ||
            !target ||
            !["completed", "partial"].includes(target.state) ||
            (!Object.keys(sources).length && !web)
          }
        >
          {busy ? "Registrando solicitud…" : "Iniciar comparación"}
        </button>
      </form>
      <h2>Historial de comparaciones</h2>
      <ErrorMessage message={history.error?.message ?? ""} />
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Documento</th>
              <th>Estado</th>
              <th>Fuentes seleccionadas</th>
            </tr>
          </thead>
          <tbody>
            {history.data?.items.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`/auditorias/${a.id}`}>{a.target.name}</Link>
                </td>
                <td>{auditStateNames[a.state]}</td>
                <td>{a.sources.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {history.data?.items.length === 0 && (
          <p>Aún no hay comparaciones visibles para tu cuenta.</p>
        )}
      </div>
      <div className="pagination">
        <button
          type="button"
          className="secondary"
          disabled={!historyOffset}
          onClick={() => setHistoryOffset((v) => Math.max(0, v - 25))}
        >
          Comparaciones anteriores
        </button>
        <button
          type="button"
          className="secondary"
          disabled={history.data?.items.length !== 25}
          onClick={() => setHistoryOffset((v) => v + 25)}
        >
          Comparaciones siguientes
        </button>
      </div>
    </section>
  );
}
