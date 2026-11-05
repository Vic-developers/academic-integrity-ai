# API documental — Fase 2

Prefijo `/api/v1`, sesión y membresía activas. Mutaciones requieren Origin configurado, X-Requested-With y CSRF ligado a sesión. OpenAPI real: `/api/openapi.json`.

| Ruta | Comportamiento |
|---|---|
| POST /documents | Multipart `files` repetido, `assignment_id` y `owner_id` opcionales; 202 con `items` y `errors` por índice |
| GET /documents/limits | Límites configurados y disponibilidad OCR real |
| GET /documents | Lista visible con limit (1–100) y offset |
| GET /documents/{id} | Estado, versión, hash, errores, metadatos, advertencias y permiso de gestión |
| GET /documents/{id}/original | Original privado, como adjunto; no URL pública |
| GET /documents/{id}/fragments | limit/offset y filtro page opcional; original/normalizado/mapa/localizadores/oraciones |
| POST /documents/{id}/cancel | Cancelación de extracción pendiente/en curso; descarta resultado tardío |
| DELETE /documents/{id} | 204, acceso revocado y purga durable programada |
| GET/POST /courses | Asignaturas autorizadas; creación por docente/coordinación/administración |
| GET/POST /assignments | Actividades autorizadas |
| POST /courses/{id}/enrollments | Matrícula de estudiante activo en la institución |
| GET /courses/{id}/students | Directorio mínimo y matrícula para quien gestiona esa asignatura |
| GET /course-teachers | Candidatos a docente de la institución, con permiso de gestión |

El endpoint de carga autentica antes de leer el formulario. El límite total se aplica también sin confiar en Content-Length. Errores individuales no crean documentos; un PDF con firma válida pero corrupto produce un trabajo fallido con error específico tras la inspección del parser. Un resultado 202 no garantiza extracción satisfactoria. Lotes con todos los archivos inválidos pueden devolver items vacío y errors no vacío.

Los localizadores usan puntos de código Unicode, inicio inclusivo/fin exclusivo dentro de cada fragmento original; no UTF-16 ni bytes. PDF añade coordenadas pdfplumber con bbox/rotación de página. DOCX añade parte/bloque/run y marca cuando los runs no coinciden exactamente. Las API no convierten estos rangos en acusaciones ni resultados de similitud.

En esta fase los desplegables de asignaturas, actividades y directorios se limitan a 100 opciones. La administración masiva de esos catálogos se ampliará en SaaS; la lista documental y fragmentos sí tienen paginación. Cada carga crea un documento con versión inicial 1; la edición de versiones y cronología completa se implementará posteriormente. Los originales no se sobrescriben.
