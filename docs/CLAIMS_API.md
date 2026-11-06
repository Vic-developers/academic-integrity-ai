# API de afirmaciones

Todos los recursos requieren sesión e institución activa; escrituras requieren CSRF/origen. Prefijo `/api/v1/claims`. Evidencia en puntos de código Unicode, no índices UTF-16 del navegador. Los objetos desconocidos o sin acceso responden 404.

| Método y ruta | Operación |
| --- | --- |
| GET `/capabilities` | Declara recuperación local y revisión humana; NLI y descarga remota deshabilitados |
| POST `/` | `document_id`, `source_document_ids` (máximo 20), `Idempotency-Key` opcional; devuelve 202 y trabajo durable |
| GET `/` | Revisiones visibles, `limit` 1–100, `offset` ≥0 |
| GET `/{id}` | Estado, snapshots, límites y conteos de evaluación humana |
| GET `/{id}/items` | Afirmaciones paginadas con última revisión |
| GET `/{id}/items/{claim}` | Afirmación e historial completo |
| GET `/{id}/fragments` | Fragmentos originales paginados del principal, o fuente seleccionada con `source_id` |
| POST `/{id}/items` | Añade afirmación manual sobre intervalo verificado del principal |
| POST `/{id}/items/{claim}/review` | Decisión humana, revisión optimista y pasajes verificados |
| POST `/{id}/cancel` | Cancela trabajo pendiente/en ejecución |
| GET `/{id}/export` | JSON privado con snapshots, originales, hashes e historial |

Un intervalo contiene `fragment_id`, `original_start`, `original_end`, `fragment_sha256`, `span_sha256`. El texto lo reconstruye el servidor. En una evaluación, cada pasaje añade `source_id` de esta revisión; no admite documentos arbitrarios. Un cuerpo de revisión contiene `expected_revision`, `state`, `reason` (10–2000 caracteres) y `passages` (hasta cinco). Estados: `unreviewed`, `supported`, `contradicted`, `partially_supported`, `not_verifiable`, `insufficient_source`. Los tres estados afirmativos requieren pasajes. Solo evaluadores autorizados pueden evaluar/agregar; el estudiante recibe 403.

Errores: 409 revisión obsoleta/hash cambiado/estado incompatible/idempotencia conflictiva; 422 intervalo o evidencia incompletos; 413 cuerpo >64 KiB o presupuesto combinado excedido; 429 frecuencia excedida. Máximo 30 creaciones por solicitante cada quince minutos. Las funciones SQL internas de trabajos no son una API pública.

Consulta [alcance y límites](PHASE_7.md). No existe endpoint de inferencia NLI ni verificación de verdad automática.
