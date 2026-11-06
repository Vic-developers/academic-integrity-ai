import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { sha256 } from "../evidence";
import { claimStates, claimRunStates, claimLimits } from "../claims";
import type { ClaimRun, ClaimItem, Passage, Span } from "../claims";
import ErrorMessage from "../components/ErrorMessage";

type Fragment = {
  id: string;
  original: string;
  fragment_sha256: string;
  page: number | null;
  paragraph: number;
};
// Offsets are explicitly Unicode code points, matching backend storage, including emoji.
function SpanPicker({
  path,
  sourceId,
  onChoose,
}: {
  path: string;
  sourceId?: string;
  onChoose: (span: Span) => Promise<void>;
}) {
  const [offset, setOffset] = useState(0);
  const [chosen, setChosen] = useState("");
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [error, setError] = useState("");
  const data = useQuery({
    queryKey: ["claim-fragments", path, sourceId, offset],
    queryFn: () =>
      api<{ items: Fragment[] }>(
        `${path}/fragments?limit=25&offset=${offset}${sourceId ? `&source_id=${sourceId}` : ""}`,
      ),
    gcTime: 0,
    refetchInterval: 10000,
  });
  if (data.error) return <ErrorMessage message={data.error.message} />;
  const fragment = data.data?.items.find((f) => f.id === chosen);
  return (
    <div className="panel">
      <label>
        Fragmento original
        <select
          value={chosen}
          onChange={(e) => {
            setChosen(e.target.value);
            setStart(0);
            const f = data.data?.items.find((f) => f.id === e.target.value);
            setEnd(f ? Math.min(Array.from(f.original).length, 2000) : 0);
          }}
        >
          <option value="">Selecciona un fragmento</option>
          {data.data?.items.map((f) => (
            <option key={f.id} value={f.id}>
              Párrafo {f.paragraph} · página {f.page ?? "—"}
            </option>
          ))}
        </select>
      </label>
      {fragment && (
        <>
          <blockquote style={{ whiteSpace: "pre-wrap" }}>
            {fragment.original}
          </blockquote>
          <p>
            Intervalo en puntos de código Unicode: inicio incluido, fin
            excluido. Longitud: {Array.from(fragment.original).length}; máximo
            2000 por selección.
          </p>
          <label>
            Inicio
            <input
              type="number"
              min={0}
              value={start}
              onChange={(e) => setStart(Number(e.target.value))}
            />
          </label>
          <label>
            Fin
            <input
              type="number"
              min={1}
              value={end}
              onChange={(e) => setEnd(Number(e.target.value))}
            />
          </label>
          <blockquote>
            {Array.from(fragment.original).slice(start, end).join("")}
          </blockquote>
          <button
            onClick={async () => {
              setError("");
              try {
                const chars = Array.from(fragment.original);
                if (
                  !Number.isInteger(start) ||
                  !Number.isInteger(end) ||
                  start < 0 ||
                  end <= start ||
                  end > chars.length ||
                  end - start > 2000
                )
                  throw new Error("Intervalo inválido");
                const text = chars.slice(start, end).join("");
                await onChoose({
                  fragment_id: fragment.id,
                  original_start: start,
                  original_end: end,
                  fragment_sha256: fragment.fragment_sha256,
                  span_sha256: await sha256(text),
                  text,
                  page: fragment.page,
                  paragraph: fragment.paragraph,
                });
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Usar este pasaje
          </button>
        </>
      )}
      <ErrorMessage message={error} />
      <div className="pagination">
        <button
          disabled={!offset}
          onClick={() => {
            setOffset((v) => Math.max(0, v - 25));
            setChosen("");
          }}
        >
          Fragmentos anteriores
        </button>
        <button
          disabled={data.data?.items.length !== 25}
          onClick={() => {
            setOffset((v) => v + 25);
            setChosen("");
          }}
        >
          Fragmentos siguientes
        </button>
      </div>
    </div>
  );
}

function Review({
  claim,
  run,
  path,
  onSaved,
}: {
  claim: ClaimItem;
  run: ClaimRun;
  path: string;
  onSaved: () => Promise<unknown>;
}) {
  const [revision, setRevision] = useState(claim.review_revision);
  const [state, setState] = useState(claim.review_state);
  const [reason, setReason] = useState("");
  const [selected, setSelected] = useState<Passage[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  function add(p: Passage) {
    setSelected((v) => (v.length < 5 ? [...v, p] : v));
  }
  return (
    <div>
      <h3>Evaluación humana</h3>
      <p>
        Revisión cargada: {revision}. Actual: {claim.review_revision}. El
        borrador se conserva si otra persona guarda cambios.
      </p>
      <button
        className="secondary"
        onClick={() => setRevision(claim.review_revision)}
      >
        Usar revisión actual conservando borrador
      </button>
      <label>
        Clasificación
        <select value={state} onChange={(e) => setState(e.target.value)}>
          {Object.entries(claimStates).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </label>
      <label>
        Motivo
        <textarea
          minLength={10}
          maxLength={2000}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </label>
      <p>Pasajes adjuntos: {selected.length}/5</p>
      {selected.map((p, i) => (
        <div key={i}>
          <blockquote>{p.span.text}</blockquote>
          <button
            className="secondary"
            onClick={() => setSelected((v) => v.filter((_, j) => i !== j))}
          >
            Quitar pasaje {i + 1}
          </button>
        </div>
      ))}
      {claim.evidence.candidates.map((p, i) => (
        <div className="panel" key={i}>
          <p>
            Pasaje sugerido por palabras compartidas ·{" "}
            {run.sources.find((s) => s.id === p.source_id)?.name}. No determina
            respaldo.
          </p>
          <blockquote>{p.span.text}</blockquote>
          <p>
            Página {p.span.page ?? "—"} · párrafo {p.span.paragraph} · [
            {p.span.original_start}, {p.span.original_end})
          </p>
          <button disabled={selected.length >= 5} onClick={() => add(p)}>
            Adjuntar sugerencia {i + 1}
          </button>
        </div>
      ))}
      <details>
        <summary>Buscar otro pasaje en las fuentes seleccionadas</summary>
        <label>
          Fuente
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
          >
            <option value="">Selecciona una fuente</option>
            {run.sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        {sourceId && (
          <SpanPicker
            key={sourceId}
            path={path}
            sourceId={sourceId}
            onChoose={async (span) => {
              if (selected.length >= 5) throw new Error("Máximo 5 pasajes");
              add({ source_id: sourceId, span });
            }}
          />
        )}
      </details>
      <ErrorMessage message={error} />
      <button
        disabled={busy || reason.trim().length < 10}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const saved = await api<ClaimItem>(
              `${path}/items/${claim.id}/review`,
              {
                expected_revision: revision,
                state,
                reason,
                passages: selected.map((p) => ({
                  source_id: p.source_id,
                  ...Object.fromEntries(
                    Object.entries(p.span).filter(([k]) =>
                      [
                        "fragment_id",
                        "original_start",
                        "original_end",
                        "fragment_sha256",
                        "span_sha256",
                      ].includes(k),
                    ),
                  ),
                })),
              },
            );
            setRevision(saved.review_revision);
            await onSaved();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        Guardar evaluación humana
      </button>
    </div>
  );
}
export default function ClaimResult({ canReview }: { canReview: boolean }) {
  const { id } = useParams();
  const path = `/claims/${id}`;
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<unknown>(null);
  const run = useQuery({
    queryKey: ["claim-run", id],
    queryFn: () => api<ClaimRun>(path),
    gcTime: 0,
    refetchInterval: (q) =>
      ["pending", "running"].includes(q.state.data?.state ?? "") ? 1500 : 10000,
  });
  const items = useQuery({
    queryKey: ["claim-items", id, offset, run.data?.state],
    queryFn: () =>
      api<{ items: ClaimItem[] }>(`${path}/items?limit=25&offset=${offset}`),
    enabled: !!run.data,
    gcTime: 0,
    refetchInterval: 10000,
  });
  if (run.error || items.error)
    return <ErrorMessage message={(run.error || items.error)!.message} />;
  if (!run.data) return <p role="status">Cargando afirmaciones…</p>;
  const r = run.data;
  const finished = ["completed", "partial"].includes(r.state);
  async function refresh() {
    await Promise.all([run.refetch(), items.refetch()]);
  }
  return (
    <section className="claims-workspace">
      <Link to="/afirmaciones">Volver a afirmaciones</Link>
      <h1>Revisión de afirmaciones</h1>
      <h2>{r.target.name}</h2>
      <p role="status">
        Estado: {claimRunStates[r.state] ?? r.state} · Afirmaciones:{" "}
        {r.summary.claims_total} · Evaluadas por personas:{" "}
        {r.summary.human_reviewed}
      </p>
      <p>
        La extracción es heurística y puede omitir frases. La recuperación es
        léxica: no interpreta negaciones, causalidad ni respaldo científico. No
        se consultaron fuentes externas ni modelos NLI.
      </p>
      <p>
        Versión principal: {r.target.version_id}. SHA-256:{" "}
        <code>{r.target.sha256}</code>
      </p>
      <details>
        <summary>Fuentes y límites</summary>
        {r.sources.map((s) => (
          <p key={s.id}>
            {s.name} · versión {s.version_id} · SHA-256 <code>{s.sha256}</code>
          </p>
        ))}
        {!r.sources.length && <p>No hay fuentes seleccionadas.</p>}
        {r.summary.extraction_partial && (
          <p>La extracción de al menos un documento es parcial.</p>
        )}
        <ul>
          {r.summary.limitations?.map((l) => (
            <li key={l}>{claimLimits[l] ?? l}</li>
          ))}
        </ul>
      </details>
      <ErrorMessage message={error} />
      <button className="secondary" onClick={() => void refresh()}>
        Actualizar revisión
      </button>
      <a className="button secondary" href={`/api/v1${path}/export`} download>
        Exportar evidencia JSON
      </a>
      {!finished && ["pending", "running"].includes(r.state) && (
        <button
          onClick={async () => {
            try {
              await api(path + "/cancel", {});
              await refresh();
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Cancelar trabajo
        </button>
      )}
      {r.error_code && <p>{r.error_code}</p>}
      {items.data?.items.map((c) => (
        <article className="panel" key={c.id}>
          <h2>Afirmación {c.ordinal}</h2>
          <p>
            {claimStates[c.review_state]} ·{" "}
            {c.evidence.origin === "manual_selection"
              ? "Selección humana"
              : "Candidata heurística"}
          </p>
          <blockquote>{c.evidence.span.text}</blockquote>
          <p>
            Página {c.evidence.span.page ?? "—"} · párrafo{" "}
            {c.evidence.span.paragraph} · [{c.evidence.span.original_start},{" "}
            {c.evidence.span.original_end}) · Unicode
          </p>
          <p>
            Citas candidatas:{" "}
            {c.evidence.citation_context.map((x) => x.label).join(", ") ||
              "ninguna detectada"}
            . La asociación con la fuente debe comprobarse.
          </p>
          {!c.evidence.candidates.length && (
            <p>No se recuperaron pasajes en la búsqueda local acotada.</p>
          )}
          {c.last_review && (
            <>
              <p>Último motivo: {c.last_review.reason}</p>
              <p>
                Evaluador: {c.last_review.actor_id} · {c.last_review.at}
              </p>
              {c.last_review.passages.map((p, i) => (
                <blockquote key={i}>{p.span.text}</blockquote>
              ))}
            </>
          )}
          {canReview && finished && (
            <Review claim={c} run={r} path={path} onSaved={refresh} />
          )}
          <button
            className="secondary"
            onClick={async () => {
              try {
                setHistory(await api(`${path}/items/${c.id}`));
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Consultar historial {c.ordinal}
          </button>
        </article>
      ))}
      <div className="pagination">
        <button
          disabled={!offset}
          onClick={() => setOffset((v) => Math.max(0, v - 25))}
        >
          Afirmaciones anteriores
        </button>
        <button
          disabled={items.data?.items.length !== 25}
          onClick={() => setOffset((v) => v + 25)}
        >
          Afirmaciones siguientes
        </button>
      </div>
      {canReview && finished && (
        <details>
          <summary>Añadir afirmación omitida</summary>
          <p>
            Selecciona un intervalo del texto principal; no se clasifica
            automáticamente.
          </p>
          <SpanPicker
            path={path}
            onChoose={async (span) => {
              await api(
                path + "/items",
                Object.fromEntries(
                  Object.entries(span).filter(([k]) =>
                    [
                      "fragment_id",
                      "original_start",
                      "original_end",
                      "fragment_sha256",
                      "span_sha256",
                    ].includes(k),
                  ),
                ),
              );
              await refresh();
            }}
          />
        </details>
      )}
      {history !== null && (
        <details open>
          <summary>Historial y trazabilidad</summary>
          <button onClick={() => setHistory(null)}>Cerrar historial</button>
          <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {JSON.stringify(history, null, 2)}
          </pre>
        </details>
      )}
    </section>
  );
}
