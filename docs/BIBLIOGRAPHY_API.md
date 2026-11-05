# Contrato bibliográfico — Fase 6

Prefijo /api/v1/bibliography, sesión/institución activa, CSRF/Origin para POST y permisos documentales. Idempotency-Key hasta 128 caracteres; cuerpo máximo 64 KiB.

| Ruta | Contrato |
|---|---|
| GET /capabilities | Disponibilidad local y habilitación efectiva de proveedores; no equivale a prueba de acceso a red |
| POST /policy | Solo admin/superadmin; {allowed:boolean}; cambia únicamente el permiso institucional; revocar cancela trabajos externos pendientes/en curso |
| POST / | 202; document_id, request_external=false, providers=[crossref,openalex]; extracción terminada o parcial; Idempotency-Key opcional |
| GET / | Historial con limit/offset 1–100; filtros de permiso antes de paginar |
| GET /{id} | Estado, snapshot, resumen, cobertura/limitaciones y candidatos de citas |
| GET /{id}/references | Referencias paginadas con campos candidatos, rangos, DOI, duplicados y lookups |
| GET /{id}/references/{ordinal} | Detalle autorizado y respuestas originales registradas para el DOI |
| POST /{id}/cancel | Cancelación; resultados tardíos descartados |
| GET /{id}/export | Descarga JSON privada, versión bibliography-evidence-v1 |

Estados de ejecución: pending/running/completed/partial/failed/cancelled/invalidated. completed significa que terminó el alcance solicitado, no que todas las referencias sean correctas. El modo local deja verification_state=not_requested y cero metadatos recuperados.

Estados de lookup separan found, not_found, disabled, not_configured, unavailable, rate_limited, rate_limited_local, unauthorized, invalid_response, response_too_large y provider_error. Un 404 solo significa ausencia en ese proveedor. Si un proveedor no se pudo consultar, el alcance externo queda parcial aunque otro devuelva datos.

Cada respuesta found conserva DOI solicitado, proveedor, HTTP 200, fecha, SHA-256 y texto JSON original en snapshot privado, sin claves ni URL con credenciales. No se guardan cuerpos de error. Referencias pueden compartir snapshot de un DOI sin duplicar el cuerpo completo; la comparación usa lo impreso en cada una.

Comparaciones: equal, partial_equal (solo primer autor candidato), different y not_compared. Un DOI válido sintácticamente no está verificado remotamente. No hay búsqueda por título ni comparación multilingüe; faltantes y diferencias requieren revisión humana. Sin permiso institucional o con servidor deshabilitado, una solicitud externa termina con cobertura parcial y cero consultas efectivas.
