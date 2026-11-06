import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { DocumentRecord } from "../documents";
import ErrorMessage from "../components/ErrorMessage";
type Details = {
  verified_writing_sample: boolean;
  authorization_reference: string;
  provenance_reference: string;
  language: string;
  domain: string;
  genre: string;
  sample_date: string;
  reason: string;
};
type Attestation = {
  revision: number;
  active: boolean;
  student_id?: string;
  details: Partial<Details>;
  history: unknown[];
};
type Report = {
  document: { name: string; version_id: string; sha256: string };
  extraction_partial: boolean;
  observation: {
    engine: string;
    flags_total: number;
    flags_returned: number;
    partial: boolean;
    format_inspection_available: boolean;
    date_observation: string;
    metadata: { name: string; display_value: string }[];
    flags: {
      kind: string;
      display_text: string;
      code_point?: string;
      unicode_name?: string;
      span: {
        fragment_id: string;
        page: number | null;
        paragraph: number;
        original_start: number;
        original_end: number;
        span_sha256: string;
      };
    }[];
  };
};
const kinds: Record<string, string> = {
  format_or_control_character: "Carácter de formato o control",
  nonbreaking_space: "Espacio inseparable",
  compatibility_normalization: "Normalización Unicode compatible",
  mixed_letter_scripts: "Alfabetos mezclados en una palabra",
  explicit_hidden_run: "Propiedad oculto declarada en DOCX",
  white_text_color: "Color blanco declarado",
  font_size_at_most_2pt: "Fuente de hasta dos puntos",
};
const metrics: Record<string, string> = {
  mattr_50: "Diversidad léxica móvil",
  hapax_ratio: "Términos de frecuencia uno",
  repeated_trigram_ratio: "Repetición de trigramas",
  sentence_length_cv: "Variación de longitud de oración",
  mean_sentence_tokens: "Tokens por oración",
  mean_word_characters: "Caracteres por token",
  punctuation_per_token: "Puntuación por token",
  paragraphs_per_100_tokens: "Párrafos por cien tokens",
};
function AttestationEditor({
  id,
  record,
  onSaved,
}: {
  id: string;
  record: Attestation;
  onSaved: () => Promise<unknown>;
}) {
  const [revision, setRevision] = useState(record.revision);
  const [active, setActive] = useState(record.revision ? record.active : false);
  const [form, setForm] = useState<Details>({
    verified_writing_sample: false,
    authorization_reference: "",
    provenance_reference: "",
    language: "es",
    domain: "",
    genre: "",
    sample_date: new Date().toISOString().slice(0, 10),
    reason: "",
    ...record.details,
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <details>
      <summary>Autorización y procedencia para comparar estilo</summary>
      <p>
        Requiere un documento asociado a un estudiante activo. La propiedad
        «Autor» del archivo no verifica identidad. Las muestras anteriores deben
        estar verificadas por una persona autorizada.
      </p>
      <p>
        Revisión del borrador: {revision}. Actual: {record.revision}.
      </p>
      <button
        className="secondary"
        onClick={() => setRevision(record.revision)}
      >
        Usar revisión actual conservando borrador
      </button>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setBusy(true);
          try {
            const result = await api<Attestation>(
              `/forensics/documents/${id}/attestation`,
              { ...form, active, expected_revision: revision },
            );
            setRevision(result.revision);
            await onSaved();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label className="checkbox">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />{" "}
          Autorización activa de uso para esta comparación
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={form.verified_writing_sample}
            onChange={(e) =>
              setForm((v) => ({
                ...v,
                verified_writing_sample: e.target.checked,
              }))
            }
          />{" "}
          Muestra anterior de escritura verificada por el evaluador
        </label>
        {(
          [
            "authorization_reference",
            "provenance_reference",
            "language",
            "domain",
            "genre",
            "sample_date",
            "reason",
          ] as const
        ).map((key) => (
          <label key={key}>
            {
              {
                authorization_reference: "Referencia de autorización",
                provenance_reference: "Registro de procedencia",
                language: "Idioma de la muestra",
                domain: "Dominio comparable",
                genre: "Género comparable",
                sample_date: "Fecha documentada de la muestra",
                reason: "Motivo del registro",
              }[key]
            }
            <input
              required
              type={key === "sample_date" ? "date" : "text"}
              minLength={
                key === "language"
                  ? 2
                  : key === "domain" || key === "genre"
                    ? 3
                    : key === "sample_date"
                      ? undefined
                      : 10
              }
              maxLength={1000}
              value={form[key]}
              onChange={(e) =>
                setForm((v) => ({ ...v, [key]: e.target.value }))
              }
            />
          </label>
        ))}
        <ErrorMessage message={error} />
        <button disabled={busy || (!record.revision && !active)}>
          Guardar autorización
        </button>
      </form>
      <details>
        <summary>Historial de autorización</summary>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
          {JSON.stringify(record.history, null, 2)}
        </pre>
      </details>
    </details>
  );
}
type StyleReport = {
  target: { name: string };
  sources: { name: string }[];
  generated_at: string;
  comparison: {
    rows: {
      feature: string;
      target: number;
      baseline_median: number;
      baseline_min: number;
      baseline_max: number;
      difference: number;
    }[];
    assessment: string;
    authorship_probability: null;
  };
  attestations: Record<string, Attestation>;
};
function StyleComparison({ id }: { id: string }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState<string[] | null>(null);
  const [offset, setOffset] = useState(0);
  const docs = useQuery({
    queryKey: ["forensic-sources", id, offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?limit=25&offset=${offset}`),
    gcTime: 0,
    refetchInterval: 10000,
  });
  const report = useQuery({
    queryKey: ["style-comparison", id, submitted],
    queryFn: async () => {
      const ids = [id, ...submitted!];
      const records = await Promise.all(
        ids.map((doc) =>
          api<Attestation>(`/forensics/documents/${doc}/attestation`),
        ),
      );
      return api<StyleReport>("/forensics/style/compare", {
        document_id: id,
        source_document_ids: submitted,
        expected_revisions: Object.fromEntries(
          ids.map((doc, i) => [doc, records[i].revision]),
        ),
      });
    },
    enabled: submitted !== null,
    gcTime: 0,
    refetchInterval: 10000,
  });
  if (docs.error) return <ErrorMessage message={docs.error.message} />;
  return (
    <details>
      <summary>Comparar con muestras anteriores autorizadas</summary>
      <p>
        Elige entre dos y cinco muestras verificadas del mismo estudiante,
        anteriores al trabajo, con idioma, dominio y género comparables. Cada
        texto debe contener cien tokens como mínimo; es un mínimo técnico, no
        suficiencia científica. No se calcula una probabilidad de autoría a
        partir de estas diferencias.
      </p>
      {docs.data?.items
        .filter((d) => d.id !== id && d.state === "completed")
        .map((d) => (
          <label className="checkbox" key={d.id}>
            <input
              type="checkbox"
              checked={selected.includes(d.id)}
              disabled={!selected.includes(d.id) && selected.length >= 5}
              onChange={(e) => {
                setSubmitted(null);
                setSelected((v) =>
                  e.target.checked ? [...v, d.id] : v.filter((x) => x !== d.id),
                );
              }}
            />
            {d.name} · <Link to={`/forense/${d.id}`}>Revisar procedencia</Link>
          </label>
        ))}
      <div className="pagination">
        <button
          disabled={!offset}
          onClick={() => setOffset((v) => Math.max(0, v - 25))}
        >
          Muestras anteriores
        </button>
        <button
          disabled={docs.data?.items.length !== 25}
          onClick={() => setOffset((v) => v + 25)}
        >
          Muestras siguientes
        </button>
      </div>
      <button
        disabled={selected.length < 2}
        onClick={() => {
          setSubmitted([...selected]);
          if (submitted?.join() === selected.join()) void report.refetch();
        }}
      >
        Comparar estilo descriptivamente
      </button>
      <ErrorMessage message={report.error?.message ?? ""} />
      {report.isFetching && <p>Consultando permisos y muestras…</p>}
      {report.data && !report.error && (
        <div className="panel">
          <h2>Comparación descriptiva, sin conclusión de autoría</h2>
          <p>
            Las diferencias pueden corresponder a tema, extensión, edición o
            extracción. No hay análisis sintáctico o semántico aprendido ni
            verificación automática de identidad.
          </p>
          <p>
            Muestras: {report.data.sources.map((s) => s.name).join(", ")}.
            Fecha: {report.data.generated_at}.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Medida</th>
                  <th>Trabajo</th>
                  <th>Mediana previa</th>
                  <th>Rango previo</th>
                  <th>Diferencia</th>
                </tr>
              </thead>
              <tbody>
                {report.data.comparison.rows.map((r) => (
                  <tr key={r.feature}>
                    <td>{metrics[r.feature] ?? r.feature}</td>
                    <td>{r.target.toFixed(4)}</td>
                    <td>{r.baseline_median.toFixed(4)}</td>
                    <td>
                      {r.baseline_min.toFixed(4)} – {r.baseline_max.toFixed(4)}
                    </td>
                    <td>{r.difference.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details>
            <summary>Trazabilidad de la comparación</summary>
            <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              {JSON.stringify(report.data, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </details>
  );
}
export default function Forensics({ canReview }: { canReview: boolean }) {
  const { id } = useParams();
  const [offset, setOffset] = useState(0);
  const docs = useQuery({
    queryKey: ["forensic-documents", offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?limit=25&offset=${offset}`),
    enabled: !id,
    gcTime: 0,
  });
  const document = useQuery({
    queryKey: ["forensic-document", id],
    queryFn: () => api<DocumentRecord>(`/documents/${id}`),
    enabled: !!id,
    gcTime: 0,
    refetchInterval: 10000,
  });
  const ready =
    document.data && ["completed", "partial"].includes(document.data.state);
  const report = useQuery({
    queryKey: ["forensic-report", id, document.data?.state],
    queryFn: () => api<Report>(`/forensics/documents/${id}`),
    enabled: !!id && !!ready,
    gcTime: 0,
    refetchInterval: 10000,
  });
  const record = useQuery({
    queryKey: ["style-attestation", id],
    queryFn: () => api<Attestation>(`/forensics/documents/${id}/attestation`),
    enabled: !!id && !!ready,
    gcTime: 0,
    refetchInterval: 10000,
  });
  if (docs.error || document.error || report.error || record.error)
    return (
      <ErrorMessage
        message={
          (docs.error || document.error || report.error || record.error)!
            .message
        }
      />
    );
  const data = report.data;
  return (
    <section className="claims-workspace">
      <h1>Forense documental y estilo</h1>
      <p>
        Las propiedades y observaciones técnicas son contexto. No demuestran
        quién escribió el documento, intención de ocultación ni uso de IA. El
        autor registrado puede proceder de una plantilla.
      </p>
      {!id ? (
        <>
          <h2>Selecciona un documento autorizado</h2>
          {docs.data?.items.map((d) => (
            <p key={d.id}>
              <Link to={`/forense/${d.id}`}>{d.name}</Link>
            </p>
          ))}
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
        </>
      ) : (
        <>
          <Link to="/forense">Volver a documentos</Link>
          {!ready && <p role="status">Espera a que termine la extracción.</p>}
          {ready && !data && <p role="status">Calculando observaciones…</p>}
          {data && (
            <>
              <h2>{data.document.name}</h2>
              <p role="status">
                Observaciones: {data.observation.flags_returned} de{" "}
                {data.observation.flags_total}.
              </p>
              {data.extraction_partial && (
                <p>
                  Extracción parcial: el análisis no cubre todo el documento.
                </p>
              )}
              {!data.observation.format_inspection_available && (
                <p>
                  La inspección de formato no está disponible en esta
                  extracción. No equivale a ausencia de texto oculto.
                </p>
              )}
              <h2>Metadatos contextuales</h2>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Propiedad declarada</th>
                      <th>Valor observado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.observation.metadata.map((p, i) => (
                      <tr key={i}>
                        <td>{p.name}</td>
                        <td>{p.display_value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p>
                {data.observation.date_observation === "modified_before_created"
                  ? "La fecha modificada precede a la creada en los valores interpretables; requiere revisar contexto y procedencia."
                  : data.observation.date_observation ===
                      "no_reversal_in_parsed_dates"
                    ? "No se observó inversión en las fechas interpretadas."
                    : "Las fechas no pudieron compararse de forma compatible."}
              </p>
              <h2>Observaciones con ubicación original</h2>
              {data.observation.flags.map((flag, i) => (
                <article className="panel" key={i}>
                  <h3>{kinds[flag.kind] ?? flag.kind}</h3>
                  <code>{flag.display_text}</code>
                  <p>
                    {flag.code_point} {flag.unicode_name}
                  </p>
                  <p>
                    Página {flag.span.page ?? "—"} · párrafo{" "}
                    {flag.span.paragraph} · [{flag.span.original_start},{" "}
                    {flag.span.original_end}) puntos de código Unicode
                  </p>
                  <p>
                    SHA-256 del pasaje: <code>{flag.span.span_sha256}</code>
                  </p>
                </article>
              ))}
              {data.observation.partial && (
                <p>
                  Se muestran las primeras 250 observaciones; el conteo incluye
                  las restantes.
                </p>
              )}
              <p>
                Los caracteres de formato pueden tener usos legítimos. El color
                blanco puede ser visible sobre un fondo de color. Solo se
                inspeccionan propiedades explícitas; no se resuelven estilos
                heredados ni todas las capas de PDF.
              </p>
              <details>
                <summary>Procedencia del análisis</summary>
                <p>
                  Motor: {data.observation.engine}. Versión:{" "}
                  {data.document.version_id}. SHA-256:{" "}
                  <code>{data.document.sha256}</code>.
                </p>
                <p>
                  Metadatos acotados por el extractor; no se reconstruye un
                  historial de edición ausente.
                </p>
              </details>
              <p>
                <Link to={`/documentos/${id}`}>
                  Consultar documento original
                </Link>{" "}
                ·{" "}
                <a
                  href={`/api/v1/forensics/documents/${id}`}
                  download="observaciones-forenses.json"
                >
                  Exportar observaciones JSON
                </a>
              </p>
              {canReview && record.data && (
                <>
                  <AttestationEditor
                    key={id}
                    id={id!}
                    record={record.data}
                    onSaved={() => record.refetch()}
                  />
                  <StyleComparison key={"style-" + id} id={id!} />
                </>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
