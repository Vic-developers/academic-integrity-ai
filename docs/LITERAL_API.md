# API literal — Fase 3

## Corrección posterior del PDF

El visor aplica la transformación real de PDF.js a las cajas originales y admite las cuatro rotaciones, CropBox, orígenes desplazados y UserUnit. Conserva compatibilidad con versiones ya extraídas; solo omite el overlay cuando la referencia o los caracteres no son verificables. [Verificación](validation/pdf-correction/README.md).

Prefijo `/api/v1`. Sesión, institución seleccionada, CSRF y Origin se aplican como en fases anteriores. OpenAPI real: `/api/openapi.json`.

| Método y ruta | Resultado |
|---|---|
| GET /audits/capabilities | Motor, umbral, límites y disponibilidad real; web false |
| POST /audits | 202; document_id, source_document_ids (hasta 20), request_web; Idempotency-Key opcional hasta 128 caracteres |
| GET /audits | Historial autorizado, limit/offset |
| GET /audits/{id} | Estado, versiones, configuración, fuentes, cobertura, resumen y tiempos |
| GET /audits/{id}/findings | Hallazgos paginados y evidencia con rangos en ambos documentos |
| POST /audits/{id}/cancel | Cancelación autorizada; resultados tardíos descartados |

El cuerpo de creación está limitado a 64 KiB. Fuentes distintas del principal, extracción terminada o parcial, normalizador compatible y permisos efectivos en todos los documentos. Sin fuentes solo se admite una solicitud web explícita, que actualmente resulta parcial por indisponibilidad. El mismo Idempotency-Key con otra configuración produce conflicto 409.

Estados: pending, running, completed, partial, failed, cancelled, invalidated. completed solo describe el alcance local seleccionado. coverage separa fuentes seleccionadas/comparadas y web; summary cuenta palabras coincidentes sin duplicación, nunca una probabilidad de plagio. Fuentes conservan versión, SHA-256 y fecha real de consulta. Findings incluyen evidencia original y normalizada, localizadores, truncamiento y review_state pending.

Un objeto ajeno o una fuente revocada produce 404. El borrado invalida y elimina evidencia derivada. No están implementadas las rutas futuras de decisiones, exportación o recuperación de páginas web.

## Ampliación de Fase 4

- GET /audits/{audit_id}/findings/{finding_id}/view?side=target|source&range_index=0: fragmento original verificado, rangos superpuestos, geometría por carácter y versión documental.
- GET .../original?side=target|source: descarga de la versión vinculada, con todos los permisos revalidados.
- GET .../export: JSON de evidencia, procedencia y revisión, descarga privada.
- POST .../review: expected_revision, state (pending/reviewed/justified/dismissed/confirmed), citation (pending_review/correct/absent/incomplete), reason (5–2000 caracteres, significativo). Devuelve review_state, review_revision y review_log. Máximo 100 cambios; conflicto 409 si revisión obsoleta.

Listados de hallazgos añaden review_revision y review_log. Los estudiantes no pueden guardar revisión. Los offsets se refieren a puntos de código del fragmento original. PDF rotado/recortado no obtiene overlay si PDF.js y geometría no coinciden; la evidencia textual sigue verificable.
