import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { queryClient } from "../query";
import type { AuditRecord, LiteralFinding } from "../audits";
import type { ReviewState } from "../evidence";
import { reviewNames } from "../evidence";
import EvidencePane from "../components/EvidencePane";
import ErrorMessage from "../components/ErrorMessage";
export default function EvidenceViewer({ canReview }: { canReview: boolean }) {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const [filter, setFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [bookmarks, setBookmarks] = useState<string[]>([]);
  const [state, setState] = useState<ReviewState>("reviewed");
  const [citation, setCitation] = useState("pending_review");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [editingRevision, setEditingRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const audit = useQuery({
    queryKey: ["audit", id],
    queryFn: () => api<AuditRecord>(`/audits/${id}`),
    refetchInterval: 10000,
    gcTime: 0,
  });
  const findings = useQuery({
    queryKey: ["viewer-findings", id],
    queryFn: async () => {
      const all: LiteralFinding[] = [];
      for (let offset = 0; offset < 500; offset += 100) {
        const batch = await api<{ items: LiteralFinding[] }>(
          `/audits/${id}/findings?limit=100&offset=${offset}`,
        );
        all.push(...batch.items);
        if (batch.items.length < 100) break;
      }
      return all;
    },
    enabled: Boolean(
      audit.data && ["completed", "partial"].includes(audit.data.state),
    ),
    refetchInterval: 10000,
    gcTime: 0,
  });
  const visible = (findings.data ?? []).filter(
    (f) =>
      (filter === "all" || filter === "bookmarked"
        ? filter !== "bookmarked" || bookmarks.includes(f.id)
        : f.review_state === filter) &&
      (sourceFilter === "all" || f.source_id === sourceFilter),
  );
  const selected =
    visible.find((f) => f.id === params.get("finding")) ?? visible[0];
  const position = visible.findIndex((f) => f.id === selected?.id);
  function select(finding: string) {
    setParams({ finding }, { replace: true });
  }
  useEffect(() => {
    setEditingRevision(selected?.review_revision ?? 0);
    setReason("");
    setError("");
    setState(
      selected?.review_state === "pending"
        ? "reviewed"
        : (selected?.review_state ?? "reviewed"),
    );
    setCitation(selected?.review_log.at(-1)?.citation ?? "pending_review");
  }, [selected?.id]);
  if (audit.error || findings.error)
    return <ErrorMessage message={(audit.error || findings.error)!.message} />;
  if (!audit.data) return <p role="status">Cargando visor…</p>;
  const record = audit.data;
  return (
    <section className="evidence-workspace">
      <Link to={`/auditorias/${id}`}>← Resultado y cobertura</Link>
      <h1>Visor de evidencias</h1>
      <p>
        Coincidencias verificables, decisión humana. Los colores indican
        categoría o revisión; no culpabilidad.
      </p>
      <div className="viewer-tools panel evidence-filters">
        <label>
          Filtrar revisión
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">Todas</option>
            <option value="bookmarked">Marcadas en esta sesión</option>
            {Object.entries(reviewNames).map(([key, name]) => (
              <option key={key} value={key}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Filtrar fuente
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="all">Todas las fuentes</option>
            {record.sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <button
          className="secondary"
          disabled={position <= 0}
          onClick={() => select(visible[position - 1].id)}
        >
          Coincidencia anterior
        </button>
        <span role="status">
          {selected
            ? `${position + 1} de ${visible.length} coincidencias`
            : "Sin coincidencias para este filtro"}
        </span>
        <button
          className="secondary"
          disabled={position < 0 || position + 1 >= visible.length}
          onClick={() => select(visible[position + 1].id)}
        >
          Coincidencia siguiente
        </button>
      </div>
      {findings.isPending && <p role="status">Cargando hallazgos…</p>}
      {selected && (
        <>
          <div className="viewer-tools">
            <label>
              Seleccionar coincidencia
              <select
                value={selected.id}
                onChange={(e) => select(e.target.value)}
              >
                {visible.map((f, i) => (
                  <option key={f.id} value={f.id}>
                    {i + 1}.{" "}
                    {record.sources.find((s) => s.id === f.source_id)?.name} ·{" "}
                    {f.word_count} palabras · {reviewNames[f.review_state]}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="secondary"
              aria-pressed={bookmarks.includes(selected.id)}
              onClick={() =>
                setBookmarks((b) =>
                  b.includes(selected.id)
                    ? b.filter((x) => x !== selected.id)
                    : [...b, selected.id],
                )
              }
            >
              {bookmarks.includes(selected.id)
                ? "★ Quitar marcador"
                : "☆ Marcar coincidencia"}
            </button>
          </div>
          <div className="comparison-panes">
            <EvidencePane
              key={`target-${selected.id}`}
              auditId={id}
              findingId={selected.id}
              side="target"
              onSelect={select}
            />
            <EvidencePane
              key={`source-${selected.id}`}
              auditId={id}
              findingId={selected.id}
              side="source"
              onSelect={select}
            />
          </div>
          <section
            className="panel explanation"
            aria-label="Explicación y revisión"
          >
            <h2>Coincidencia textual normalizada</h2>
            <a href={`/api/v1/audits/${id}/findings/${selected.id}/export`}>
              Exportar evidencia JSON
            </a>
            <p>{selected.evidence.explanation}</p>
            <p>
              Estado humano:{" "}
              <strong>{reviewNames[selected.review_state]}</strong> · Citación:{" "}
              {
                (
                  {
                    pending_review: "Pendiente de comprobación",
                    correct: "Correcta",
                    absent: "Ausente",
                    incomplete: "Incompleta",
                  } as Record<string, string>
                )[selected.review_log.at(-1)?.citation ?? "pending_review"]
              }
            </p>
            <p className="small">
              Confirmar significa validar esta coincidencia textual; no declara
              una infracción académica. Los cambios quedan registrados con
              motivo y evaluador.
            </p>
            {canReview && editingRevision !== selected.review_revision && (
              <div className="notice">
                <p>
                  La revisión cambió mientras trabajabas. Lee el historial antes
                  de cargar la revisión actual; tu motivo se conserva.
                </p>
                <button
                  className="secondary"
                  onClick={() => {
                    setEditingRevision(selected.review_revision);
                    setState(selected.review_state);
                    setCitation(
                      selected.review_log.at(-1)?.citation ?? "pending_review",
                    );
                    setError("");
                  }}
                >
                  Cargar revisión actual
                </button>
              </div>
            )}
            {canReview && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  setBusy(true);
                  setError("");
                  try {
                    const saved = await api<{ review_revision: number }>(
                      `/audits/${id}/findings/${selected.id}/review`,
                      {
                        expected_revision: editingRevision,
                        state,
                        citation,
                        reason,
                      },
                    );
                    setEditingRevision(saved.review_revision);
                    setReason("");
                    await queryClient.invalidateQueries({
                      queryKey: ["viewer-findings", id],
                    });
                    await queryClient.invalidateQueries({
                      queryKey: ["evidence-view", id],
                    });
                    await queryClient.invalidateQueries({
                      queryKey: ["findings", id],
                    });
                  } catch (e) {
                    setError((e as Error).message);
                    await queryClient.invalidateQueries({
                      queryKey: ["viewer-findings", id],
                    });
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <div className="review-fields">
                  <label>
                    Estado de revisión
                    <select
                      value={state}
                      onChange={(e) => setState(e.target.value as ReviewState)}
                    >
                      {Object.entries(reviewNames).map(([key, name]) => (
                        <option value={key} key={key}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Valoración de la citación
                    <select
                      value={citation}
                      onChange={(e) => setCitation(e.target.value)}
                    >
                      <option value="pending_review">
                        Pendiente de comprobación
                      </option>
                      <option value="correct">Correcta</option>
                      <option value="absent">Ausente</option>
                      <option value="incomplete">Incompleta</option>
                    </select>
                  </label>
                </div>
                <label>
                  Motivo de la revisión
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    minLength={5}
                    maxLength={2000}
                    required
                  />
                </label>
                <ErrorMessage message={error} />
                <button disabled={busy || reason.trim().length < 5}>
                  {busy ? "Guardando…" : "Guardar revisión humana"}
                </button>
              </form>
            )}
            {!canReview && (
              <p>La revisión está reservada a evaluadores autorizados.</p>
            )}
            <details>
              <summary>
                Historial de revisión ({selected.review_log.length})
              </summary>
              {!selected.review_log.length && (
                <p>Sin decisiones humanas registradas.</p>
              )}
              {selected.review_log.map((event) => (
                <article key={event.revision}>
                  <strong>{reviewNames[event.state]}</strong>
                  <p>{event.reason}</p>
                  <p className="small">
                    {new Date(event.at).toLocaleString("es")} · Evaluador{" "}
                    {event.actor_id} · Revisión {event.revision}
                  </p>
                </article>
              ))}
            </details>
          </section>
        </>
      )}
    </section>
  );
}
