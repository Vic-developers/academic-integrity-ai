import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { DocumentRecord } from "../documents";
import ErrorMessage from "../components/ErrorMessage";
const descriptions: Record<string, [string, string]> = {
  mattr_50: [
    "Diversidad léxica móvil",
    "Promedio de términos distintos dividido entre el tamaño de cada ventana, hasta 50 tokens.",
  ],
  hapax_ratio: [
    "Términos que aparecen una sola vez",
    "Número de términos de frecuencia uno dividido entre todos los tokens.",
  ],
  repeated_trigram_ratio: [
    "Repetición de secuencias de tres tokens",
    "Ocurrencias adicionales de trigramas repetidos divididas entre todos los trigramas.",
  ],
  sentence_length_cv: [
    "Variación de longitud de oraciones",
    "Desviación estándar dividida entre la longitud media; segmentación por puntuación y saltos.",
  ],
  mean_sentence_tokens: [
    "Longitud media de oración",
    "Tokens por oración reconocida. No mide complejidad sintáctica.",
  ],
  mean_word_characters: [
    "Longitud media de token",
    "Puntos de código por token normalizado.",
  ],
  punctuation_per_token: [
    "Puntuación por token",
    "Caracteres de puntuación Unicode divididos entre el número de tokens.",
  ],
  paragraphs_per_100_tokens: [
    "Párrafos por cien tokens",
    "Párrafos no vacíos separados por líneas en blanco; depende de la extracción.",
  ],
};
type Observation = {
  document: {
    name: string;
    version_id: string;
    sha256: string;
    extraction_state: string;
  };
  scope: string;
  trained_on_this_document: false;
  model: null;
  observation: {
    engine: string;
    text_sha256: string;
    counts: {
      tokens: number;
      distinct_tokens: number;
      sentences: number;
      paragraphs: number;
      unicode_code_points: number;
      mattr_window: number;
    };
    values: Record<string, number>;
    assessment: "not_conclusive";
    authorship_probability: null;
    abstention_reasons: string[];
  };
};
export default function ExperimentalAI() {
  const { id } = useParams();
  const [offset, setOffset] = useState(0);
  const docs = useQuery({
    queryKey: ["experimental-docs", offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?limit=25&offset=${offset}`),
    enabled: !id,
    gcTime: 0,
  });
  const document = useQuery({
    queryKey: ["experimental-document", id],
    queryFn: () => api<DocumentRecord>(`/documents/${id}`),
    enabled: !!id,
    gcTime: 0,
    refetchInterval: 10000,
  });
  const ready =
    document.data && ["completed", "partial"].includes(document.data.state);
  const report = useQuery({
    queryKey: ["experimental-observations", id, document.data?.state],
    queryFn: () => api<Observation>(`/experimental-ai/documents/${id}`),
    enabled: !!id && !!ready,
    gcTime: 0,
    refetchInterval: 15000,
  });
  if (docs.error || document.error || report.error)
    return (
      <ErrorMessage
        message={(docs.error || document.error || report.error)!.message}
      />
    );
  const data = report.data;
  return (
    <section className="claims-workspace">
      <h1>Observaciones lingüísticas</h1>
      <p>
        Este módulo experimental describe el texto extraído. La diversidad, la
        repetición y la longitud de las frases dependen del género, el idioma,
        la extensión y la edición. No identifican quién escribió el documento.
      </p>
      <div className="panel">
        <h2>Resultado no concluyente</h2>
        <p>
          No hay un clasificador de autoría aprobado ni una probabilidad de uso
          de IA. Los documentos institucionales no se utilizan para entrenar
          modelos. Estas observaciones no deben ser el fundamento exclusivo de
          una sanción.
        </p>
      </div>
      {!id ? (
        <>
          <h2>Selecciona un documento autorizado</h2>
          {docs.data?.items.map((d) => (
            <p key={d.id}>
              <Link to={`/indicios-ia/${d.id}`}>{d.name}</Link>
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
          <Link to="/indicios-ia">Volver a documentos</Link>
          {!ready && (
            <p role="status">
              Espera a que termine la extracción del documento.
            </p>
          )}
          {ready && !data && (
            <p role="status">Calculando observaciones locales…</p>
          )}
          {data && (
            <>
              <h2>{data.document.name}</h2>
              <p>
                Tokens: {data.observation.counts.tokens} · Términos distintos:{" "}
                {data.observation.counts.distinct_tokens} · Oraciones
                reconocidas: {data.observation.counts.sentences} · Párrafos:{" "}
                {data.observation.counts.paragraphs}
              </p>
              {data.observation.counts.tokens < 100 && (
                <p role="status">
                  Texto corto: menos de cien tokens. Sus estadísticas dependen
                  especialmente de la extensión.
                </p>
              )}
              {data.document.extraction_state === "partial" && (
                <p>
                  Extracción parcial: las observaciones describen únicamente el
                  contenido recuperado.
                </p>
              )}
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Medición</th>
                      <th>Valor observado</th>
                      <th>Definición y límite</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.observation.values).map(
                      ([key, value]) => (
                        <tr key={key}>
                          <td>{descriptions[key]?.[0] ?? key}</td>
                          <td>
                            {value.toLocaleString("es", {
                              maximumFractionDigits: 4,
                            })}
                          </td>
                          <td>
                            {descriptions[key]?.[1] ?? "Medida experimental"}
                            {key === "mattr_50" &&
                              ` Ventana aplicada: ${data.observation.counts.mattr_window}.`}
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
              <details>
                <summary>Procedencia y límites</summary>
                <p>
                  Motor: {data.observation.engine}. Solo estadísticas léxicas;
                  no hay análisis semántico ni sintáctico aprendido.
                </p>
                <p>Versión documental: {data.document.version_id}</p>
                <p>
                  SHA-256 del archivo: <code>{data.document.sha256}</code>
                </p>
                <p>
                  SHA-256 del texto medido:{" "}
                  <code>{data.observation.text_sha256}</code>. Fragmentos
                  originales unidos por dos saltos de línea.
                </p>
                <p>
                  El entrenamiento y la calibración de investigación se ejecutan
                  fuera de la aplicación sobre un corpus explícitamente
                  autorizado. Ningún experimento se activa automáticamente.
                </p>
              </details>
              <p>
                <Link to={`/documentos/${id}`}>Consultar original</Link>
              </p>
              <button
                className="secondary"
                onClick={() => void report.refetch()}
              >
                Recalcular observaciones
              </button>
            </>
          )}
        </>
      )}
    </section>
  );
}
