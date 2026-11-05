export type AuditSnapshot = {
  document_id: string;
  version_id: string;
  name: string;
  sha256: string;
  extractor: string;
  extraction_state: string;
  extraction_warnings: string[];
  consulted_at?: string;
  verification?: string;
};
export type AuditSource = AuditSnapshot & {
  id: string;
  state: string;
  reason: string | null;
};
export type AuditRecord = {
  id: string;
  state:
    | "pending"
    | "running"
    | "completed"
    | "partial"
    | "failed"
    | "cancelled"
    | "invalidated";
  target: AuditSnapshot;
  sources: AuditSource[];
  engine_version: string;
  config: { min_words: number; request_web: boolean };
  summary: { target_words?: number; matched_words?: number; findings?: number };
  coverage: {
    local?: {
      state: string;
      sources_selected: number;
      sources_compared: number;
      sources_skipped: number;
      extraction_partial: boolean;
      evidence_limited: boolean;
    };
    web?: {
      state: string;
      requested: boolean;
      reason?: string;
      queries_generated: number;
      queries_sent: number;
      sources_retrieved: number;
      sources_verified: number;
    };
  };
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
export type EvidenceRange = {
  fragment_id: string;
  page: number | null;
  paragraph: number;
  original_start: number;
  original_end: number;
  text: string;
  text_truncated: boolean;
  span_sha256: string;
};
export type LiteralFinding = {
  id: string;
  source_id: string;
  category: string;
  word_count: number;
  review_state: string;
  evidence: {
    explanation: string;
    citation: string;
    offset_unit: string;
    raw_equal: boolean | null;
    target_ranges: EvidenceRange[];
    source_ranges: EvidenceRange[];
    observed_at: string;
  };
};
export const auditStateNames: Record<AuditRecord["state"], string> = {
  pending: "Pendiente",
  running: "Comparando textos",
  completed: "Comparación completada",
  partial: "Resultado parcial",
  failed: "No se pudo completar",
  cancelled: "Cancelada",
  invalidated: "Evidencia retirada",
};
export const auditLimitations: Record<string, string> = {
  no_extractable_text: "La fuente no tiene palabras extraídas comparables.",
  budget_exhausted:
    "La fuente no se comparó porque se alcanzó un límite de recursos.",
  target_below_minimum_words:
    "El documento tiene menos palabras que el mínimo de comparación.",
  seed_budget:
    "Se alcanzó el límite de candidatos; la comparación no es exhaustiva.",
  comparison_budget:
    "Se alcanzó el límite de operaciones; la comparación no es exhaustiva.",
  findings_budget: "Se alcanzó el límite de hallazgos almacenables.",
  evidence_budget: "Se alcanzó el límite de tamaño de las evidencias.",
  engine_failed: "El motor no pudo terminar; no se emitió una conclusión.",
  engine_timeout: "Se alcanzó el tiempo máximo de comparación.",
  engine_resource_limit: "Se alcanzó un límite de recursos del motor.",
  permission_revoked:
    "Los permisos del solicitante cambiaron antes de terminar.",
  worker_retries_exhausted:
    "El trabajo se interrumpió repetidamente y requiere revisión.",
};
