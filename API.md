# API y contratos de motores

## Estado al cierre de Fase 1

API implementada de Fase 1: auth/login, auth/logout, auth/me, auth/institution, auth/password-reset/request, auth/password-reset/confirm, GET/POST users, GET activity y GET statistics. OpenAPI real en /api/openapi.json; no se sirve Swagger externo para mantener CSP sin CDN. Usuarios usa limit/offset con límite 100 en esta fase; cursores opacos quedan como objetivo. Las otras rutas de abajo siguen siendo contratos futuros.

Diseño contractual, aún sin endpoints implementados. Prefijo /api/v1; OpenAPI generado por FastAPI en Fase 1. JSON UTF-8, fechas ISO 8601 UTC, UUID opacos. Errores application/problem+json con status, code, detail y request_id, sin rutas privadas ni trazas. Listados por cursor opaco con límite máximo 100.

| Ruta prevista | Operación y autorización |
|---|---|
| POST /auth/login, /logout, /password-reset/request, /password-reset/confirm | Sesión segura, respuesta de recuperación indistinguible y rate limiting |
| GET /auth/me; POST /auth/institution | Identidad y selección de membresía autorizada |
| GET/POST /documents; GET/DELETE /documents/{id} | Propietario/asignación y permisos, carga multipart por streaming |
| GET /documents/{id}/versions/{version}/content | Descarga privada autorizada con caducidad y auditoría |
| GET /documents/{id}/fragments | Texto original y mapa, no archivos arbitrarios |
| POST /audits | Versión y motores solicitados, Idempotency-Key; 202 con job durable |
| GET /audits/{id}; POST /audits/{id}/cancel | Estado por etapa, cobertura, fallos y cancelación autorizada |
| GET /audits/{id}/findings; GET /findings/{id}/evidence | Evidencias y fuentes con aislamiento |
| POST /findings/{id}/decisions | Estado anterior esperado, motivo y actor; conflicto si revisión concurrente |
| GET/POST /cases; POST /cases/{id}/comments, /decisions, /appeals | Permisos por asignación y estudiante autorizado |
| POST /reports; GET /reports/{id}/download | Generación asíncrona y descarga privada |
| GET/POST /institutions, /users, /courses, /assignments | Administración según rol y tenant |
| GET/POST /rubrics, /defense-questions | Evidencias y validación docente |
| GET /models, /capabilities, /statistics, /activity | Versiones, disponibilidad real, métricas de BD y trazabilidad |
| GET/POST /integrations, /webhooks | Administrador; destinos aprobados, secretos nunca retornados |

401 sin sesión, 403 sin permiso de acción, 404 para objetos fuera del alcance, 409 conflicto/idempotencia, 413 límite, 415 formato no admitido, 422 contenido inválido, 429 cuota, 503 proveedor temporalmente no disponible. Reservar cuota y crear auditoría en una sola transacción. Integraciones usan credenciales de servicio con scopes y rotación, no sesiones de navegador.

## Ejecución de motores

Entrada EngineRequest: tenant_context validado, audit_id, document_version_id, fragment_ids, engine_version, config_hash, deadline y cancel_token. El motor recibe referencias autorizadas, no IDs de otros tenants elegidos libremente. Salida EngineResult: status, findings, evidence_ids, coverage, errors, timings, model_revision y abstention_reason. Candidatos y hallazgos son objetos diferentes.

Evidencia mínima: original_start/end (puntos de código Python), fragment_id, normalized_start/end, normalizer_version, source_snapshot_id, source_start/end, observed_at, source_hash, engine_version y método. PDF añade página, bounding boxes y espacio de coordenadas. Una fuente sin texto recuperado no produce coincidencia exacta verificada. Las respuestas de búsqueda son candidatos con nivel snippet_only hasta recuperar y comparar.

SearchProvider.search(query, language, limit, cursor) retorna URL, título opcional, extracto opcional y procedencia. SourceFetcher.fetch(url, policy) retorna estado HTTP, URL final aprobada, tiempo, tipo, contenido limitado y hash. ReferenceProvider.lookup(doi|metadata) retorna campos del proveedor y diferencias, nunca referencias sintetizadas. EmbeddingProvider.embed(texts, revision) retorna dimensión y revisión fija, sin cambiar silenciosamente modelo. Interfaces permiten reemplazar proveedores y registrar indisponibilidad.

## Eventos y webhooks

Envelope: event_id, schema_version, type, institution_id, resource_id, occurred_at; no incluir texto académico. Tipos audit.completed, audit.partial, audit.failed, report.ready, case.updated. Outbox y entregas al menos una vez; receptor deduplica event_id. HMAC-SHA256 sobre timestamp + punto + bytes exactos del cuerpo, encabezados de versión/key_id, tolerancia temporal y comparación constante. Reintentos acotados con jitter y cola de errores; rotación con período de doble verificación. Destinos bajo la misma protección SSRF que las fuentes. No entregar eventos de un tenant a suscriptores de otro.
