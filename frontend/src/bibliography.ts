export type BiblioSpan = {
  fragment_id: string;
  page: number | null;
  paragraph: number;
  original_start: number;
  original_end: number;
  text: string;
  text_truncated: boolean;
  span_sha256: string;
};
export type BiblioCheck = {
  field: string;
  state: string;
  printed: unknown;
  observed: unknown;
};
export type BiblioLookup = {
  state: string;
  provider: string;
  doi: string;
  attempted: boolean;
  http_status: number | null;
  retrieved_at: string | null;
  response_sha256: string | null;
  comparison: { state: string; checks: BiblioCheck[] } | null;
};
export type BiblioReference = {
  ordinal: number;
  kind: string;
  text: string;
  fields: {
    authors: string | null;
    title: string | null;
    year: number | null;
    venue: string | null;
    publisher: string | null;
    dois: string[];
    missing_fields: string[];
    parser: string;
  };
  spans: BiblioSpan[];
  duplicate_of: number | null;
  citation_state: string;
  verification_state: string;
  lookups: BiblioLookup[];
};
export type BiblioRun = {
  id: string;
  state: string;
  target: {
    name: string;
    document_id: string;
    version_id: string;
    sha256: string;
  };
  config: { request_external: boolean; providers: string[] };
  summary: {
    references?: number;
    duplicate_candidates?: number;
    unmatched_citation_candidates?: number;
    uncited_reference_candidates?: number;
    metadata_retrieved_references?: number;
    provider_attempts?: number;
  };
  heading_found: boolean | null;
  limitations: string[];
  citations: {
    kind: string;
    label: string;
    state: string;
    references: number[];
    spans: BiblioSpan[];
  }[];
  error_code: string | null;
  created_at: string;
  finished_at: string | null;
};
export const biblioStates: Record<string, string> = {
  pending: "Pendiente",
  running: "Revisando referencias",
  completed: "Revisión completada",
  partial: "Resultado parcial",
  failed: "No se pudo completar",
  cancelled: "Cancelada",
  invalidated: "Evidencia retirada",
  not_requested: "Sin consulta externa",
  identifier_missing: "Sin DOI para consultar",
  identifier_ambiguous: "Varios DOI: requiere revisión",
  lookup_incomplete: "Consulta externa incompleta",
  lookup_budget: "Límite de consultas alcanzado",
  verified: "Metadatos comparados",
  partially_verified: "Parcialmente verificada",
  inconsistent: "Diferencias de metadatos",
  not_located_in_selected_providers:
    "No localizada en los proveedores consultados",
  disabled: "Proveedor no habilitado",
  not_configured: "Proveedor sin configurar",
  unavailable: "Proveedor no accesible",
  not_found: "DOI no localizado en este proveedor",
  found: "Metadatos recuperados",
  invalid_response: "Respuesta no verificable",
  rate_limited: "Proveedor limitó la consulta",
  rate_limited_local: "Límite local de consultas",
  unauthorized: "Acceso rechazado por proveedor o red",
  provider_error: "Error del proveedor",
  response_too_large: "Respuesta excede el límite",
};
export const biblioLimitations: Record<string, string> = {
  bibliography_heading_not_found:
    "No se identificó un encabezado de bibliografía: solo se muestran menciones de DOI.",
  apa_numeric_heuristics_require_review:
    "La extracción usa patrones APA y numéricos limitados; requiere revisión humana.",
  citation_scope_before_bibliography:
    "Las citas se buscan en el texto anterior al apartado de referencias.",
  publisher_not_inferred:
    "La editorial no se deduce automáticamente del texto.",
  reference_budget: "Se alcanzó el límite de 200 referencias candidatas.",
  reference_text_budget:
    "Una referencia excedió el límite de texto y se abrevió.",
  citation_budget: "Se alcanzó el límite de candidatos de cita.",
  no_reference_candidates:
    "No se identificaron referencias con los patrones compatibles.",
};

export const biblioFields: Record<string, string> = {
  authors: "Autores",
  year: "Año",
  title: "Título",
  venue: "Revista o publicación",
  publisher: "Editorial",
};
