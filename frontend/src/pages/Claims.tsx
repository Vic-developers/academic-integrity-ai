import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { DocumentRecord } from "../documents";
import { claimRunStates } from "../claims";
import type { ClaimRun } from "../claims";
import ErrorMessage from "../components/ErrorMessage";
export default function Claims() {
  const navigate = useNavigate();
  const [target, setTarget] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [offset, setOffset] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const docs = useQuery({
    queryKey: ["claim-docs", offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?limit=25&offset=${offset}`),
    gcTime: 0,
  });
  const history = useQuery({
    queryKey: ["claim-history", historyOffset],
    queryFn: () =>
      api<{ items: ClaimRun[] }>(`/claims?limit=25&offset=${historyOffset}`),
    gcTime: 0,
  });
  if (docs.error || history.error)
    return <ErrorMessage message={(docs.error || history.error)!.message} />;
  return (
    <section className="claims-workspace">
      <h1>Análisis de afirmaciones</h1>
      <p>
        Propone frases y busca palabras compartidas en fuentes locales
        seleccionadas. Un evaluador debe interpretar el contexto y registrar su
        decisión. No hay clasificación automática de respaldo o contradicción.
      </p>
      <ErrorMessage message={error} />
      <div className="panel">
        <h2>Seleccionar documentos</h2>
        <p>
          Elige un documento principal y hasta 20 fuentes. Puedes iniciar sin
          fuentes y registrar sus limitaciones.
        </p>
        {docs.data?.items
          .filter((d) => ["completed", "partial"].includes(d.state))
          .map((d) => (
            <div key={d.id}>
              <label>
                <input
                  type="radio"
                  name="claim-target"
                  checked={target === d.id}
                  onChange={() => {
                    setTarget(d.id);
                    setSources([]);
                  }}
                />{" "}
                Principal: {d.name}
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  disabled={
                    target === d.id ||
                    (!sources.includes(d.id) && sources.length >= 20)
                  }
                  checked={sources.includes(d.id)}
                  onChange={(e) =>
                    setSources((v) =>
                      e.target.checked
                        ? [...v, d.id]
                        : v.filter((id) => id !== d.id),
                    )
                  }
                />{" "}
                Fuente: {d.name}
              </label>
            </div>
          ))}
        <p>
          Fuentes seleccionadas: {sources.length}. Principal:{" "}
          {target ? "seleccionado" : "pendiente"}.
        </p>
        <div className="pagination">
          <button
            disabled={!offset}
            onClick={() => setOffset((v) => Math.max(0, v - 25))}
          >
            Documentos anteriores
          </button>
          <button
            disabled={docs.data?.items.length !== 25}
            onClick={() => setOffset((v) => v + 25)}
          >
            Documentos siguientes
          </button>
        </div>
        <button
          disabled={!target || busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              const run = await api<ClaimRun>("/claims", {
                document_id: target,
                source_document_ids: sources,
              });
              navigate(`/afirmaciones/${run.id}`);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Preparar afirmaciones
        </button>
      </div>
      <h2>Revisiones anteriores</h2>
      {history.data?.items.map((r) => (
        <p key={r.id}>
          <Link to={`/afirmaciones/${r.id}`}>{r.target.name}</Link> ·{" "}
          {claimRunStates[r.state] ?? r.state}
        </p>
      ))}
      <div className="pagination">
        <button
          disabled={!historyOffset}
          onClick={() => setHistoryOffset((v) => Math.max(0, v - 25))}
        >
          Revisiones anteriores
        </button>
        <button
          disabled={history.data?.items.length !== 25}
          onClick={() => setHistoryOffset((v) => v + 25)}
        >
          Revisiones siguientes
        </button>
      </div>
    </section>
  );
}
