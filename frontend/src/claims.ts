export const claimStates: Record<string, string> = {
  unreviewed: "Sin evaluar",
  supported: "Respaldada (evaluación humana)",
  contradicted: "Contradicha (evaluación humana)",
  partially_supported: "Respaldo parcial (evaluación humana)",
  not_verifiable: "No verificable",
  insufficient_source: "Fuente insuficiente",
};
export type Span = {
  fragment_id: string;
  original_start: number;
  original_end: number;
  fragment_sha256: string;
  span_sha256: string;
  text: string;
  page: number | null;
  paragraph: number;
};
export type Passage = { source_id: string; span: Span };
export type ClaimItem = {
  id: string;
  ordinal: number;
  review_state: string;
  review_revision: number;
  evidence: {
    span: Span;
    origin: string;
    automatic_verdict: string;
    evidence_state: string;
    candidates: Passage[];
    citation_context: { label: string }[];
  };
  last_review: {
    reason: string;
    actor_id: string;
    at: string;
    passages: Passage[];
  } | null;
};
export type ClaimRun = {
  id: string;
  state: string;
  target: { name: string; sha256: string; version_id: string };
  sources: { id: string; name: string; sha256: string; version_id: string }[];
  summary: {
    claims_total: number;
    human_reviewed: number;
    extraction_partial?: boolean;
    limitations?: string[];
  };
  error_code?: string;
};
export const claimRunStates: Record<string, string> = {
  pending: "Pendiente",
  running: "En curso",
  completed: "Completado",
  partial: "Parcial",
  failed: "Fallido",
  cancelled: "Cancelado",
  invalidated: "Invalidado",
};
export const claimLimits: Record<string, string> = {
  heuristic_candidates_require_human_review:
    "Las candidatas heurísticas necesitan revisión humana.",
  lexical_overlap_is_not_support: "Compartir palabras no demuestra respaldo.",
  no_automatic_entailment_model:
    "No hay un modelo automático de respaldo o contradicción.",
  citation_links_are_candidates: "Las asociaciones de citas son candidatas.",
  source_passage_too_long:
    "Se omitieron pasajes de fuente mayores de 2000 caracteres.",
  source_passage_budget: "Se alcanzó el límite de 5000 pasajes de fuentes.",
  claim_text_too_long: "Se omitieron afirmaciones mayores de 2000 caracteres.",
  claim_budget: "Se alcanzó el límite de 100 afirmaciones.",
  retrieval_budget: "Se alcanzó el presupuesto de búsqueda léxica.",
  citation_context_text_budget:
    "El documento supera el presupuesto de extracción de citas; se omitió ese contexto.",
};
