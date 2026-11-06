# Modelo de datos

## Fase 9 — Forense y comparación de estilo autorizada

0009_forensics añade style_attestations con RLS forzada y FK institucionales a versión/estudiante. La fase 8 no añadió esquema, por eso desciende de 0007_claims. Borrado elimina autorización e historial. Los informes de forense/estilo se calculan con permisos actuales y no persisten resultados. [Alcance detallado](docs/PHASE_9.md).

## Fase 8 — Investigación experimental y observaciones lingüísticas

La fase 8 conserva el esquema 0007_claims. Las observaciones se recalculan desde versiones/fragments protegidos por RLS, sin tablas o resultados derivados nuevos. Experimentos offline privados fuera de la base institucional; no hay exportación de documentos para entrenamiento. [Alcance detallado](docs/PHASE_8.md).

## Fase 7 — Afirmaciones y evaluación humana

0007_claims añade claim_runs, claim_sources, claims y claim_jobs: RLS forzada, FK institucionales, idempotencia, versiones y snapshots privados. Cada afirmación conserva evidencia original y un historial humano con revisión optimista. Borrar un documento invalida y limpia todos sus resultados relacionados. [Alcance detallado](docs/PHASE_7.md).

## Fase 6 — Bibliografía local y adaptadores de metadatos

0006_bibliography añade bibliography_runs y bibliography_jobs con RLS forzada, FK compuestas, idempotencia y snapshots privados. Las funciones internas de claim/recovery tienen lease, token, intentos acotados, search_path fijo y PUBLIC revocado. institutions añade bibliography_external_allowed=false, con permiso UPDATE solo para esa columna y política RLS que exige administrador/superadministrador activo de la institución. El resto de sus columnas continúa sin permiso de escritura para aid_app.

## Continuación sin Hugging Face — Infraestructura vectorial

0005_vector crea semantic_vectors con vector(384), RLS forzada, FK compuesta a institución/versión/fragmento, identidad de modelo y chunker, rangos originales, hashes, norma unitaria y caché única. Añade unicidad compuesta a document_fragments. Instala la extensión vector si falta; el downgrade conserva esa extensión compartida y elimina solo la tabla/constraint nuevas. No se modifican migraciones históricas.

El índice B-tree limita el alcance por institución/modelo/chunker/versión. La búsqueda es exacta por distancia coseno, sin índice aproximado HNSW/IVFFlat. El alcance autorizado y las fuentes elegidas se filtran antes de top-k. Se prevén como máximo 200 pasajes por versión/modelo/chunker y 20 fuentes por consulta.

## Estado actual — Fase 4

0004_review añade findings.review_revision y review_log, valores por defecto y CHECK de estados humanos permitidos. El historial conserva actor/fecha/motivo/citación; se elimina con la evidencia derivada cuando se borra la fuente. Las migraciones 0001–0003 permanecen congeladas.

## Antecedente — Fase 3

0003_literal añade audits, audit_sources, findings y audit_jobs con RLS forzada, FK compuestas, unicidad de idempotencia y funciones internas claim_audit_job/fail_exhausted_audit_jobs con search_path fijo y PUBLIC revocado. Las migraciones previas no cambian. Snapshots y rangos se guardan en JSON acotado; borrar una fuente elimina derivados e invalida la auditoría.


## Antecedente histórico — Fase 2

La migración 0002_documents añade courses, assignments, enrollments, documents, document_versions, document_fragments y document_jobs, con RLS forzada y FK compuestas. claim_document_job y fail_exhausted_document_jobs son funciones SECURITY DEFINER de uso interno con search_path fijo, privilegios revocados a PUBLIC y salida mínima. La primera migración permanece congelada.

## Antecedente histórico — cierre de Fase 1

Esquema efectivo de Fase 1: users, institutions, memberships, sessions, reset_tokens, email_jobs y activity, más alembic_version. Roles como valores restringidos por CHECK; catálogos de permisos y entidades documentales se implementarán después. Identidad global interna y tablas tenant tienen controles diferentes, descritos en [DEVELOPMENT](docs/DEVELOPMENT.md). El resto es diseño objetivo.

PostgreSQL 16 y extensión pgvector como base propuesta. UUID como PK, timestamps UTC con zona, SHA-256 para integridad. Todos los registros de negocio llevan institution_id NOT NULL; índices comienzan por institución y criterio de acceso. Tablas globales de permisos y catálogos de modelos no contienen documentos ni datos de alumnos.

## Entidades y relaciones

| Entidades | Campos y relaciones principales |
|---|---|
| Institutions, Settings | nombre, estado, política de retención, cuotas; Settings UNIQUE(institution_id,key) |
| Users, Memberships | identidad global mínima; Memberships UNIQUE(institution_id,user_id), estado; datos académicos por tenant |
| Roles, Permissions, RolePermissions, MembershipRoles | catálogo de permisos y asignación por membresía, sin elevación entre instituciones |
| Sessions, PasswordResetTokens | hash del token, usuario, vencimiento, revocación, uso único; nunca token en claro |
| Courses, Assignments, Enrollments | curso e institución, actividad, matrícula y docente autorizado |
| Documents | propietario/membresía, actividad opcional, título, estado, deleted_at |
| DocumentVersions | documento, ordinal, hash, object_key, MIME detectado, tamaño, metadatos; UNIQUE(tenant,document,ordinal) |
| DocumentSections, DocumentFragments | versión, orden, página/párrafo/oración, texto original, normalizado, mapa y versión del extractor |
| Audits, AuditJobs | documento-versión, solicitante, alcance, configuración inmutable; job con lease, intentos y error tipado |
| OutboxEvents | evento, agregado, payload mínimo, intentos, published_at; publicación idempotente |
| Findings, FindingEvidence | auditoría, categoría, estado de revisión; evidencia con rangos, snapshot, explicación y versión de motor |
| Sources, SourceSnapshots | URL canónica/documento institucional, título/autor opcionales; consulta, hash y contenido recuperado privado |
| TextMatches, SemanticMatches | finding_id, rangos en ambos lados, tokens o similitud, algoritmo, umbral; no mezclar escalas |
| FragmentEmbeddings | fragmento, modelo/revisión, dimensión y vector; UNIQUE(tenant,fragment,model) |
| BibliographicReferences, ReferenceChecks | referencia extraída, rango, DOI candidato; proveedor, consulta, respuesta, fecha, diferencias y estado |
| Claims, ClaimChecks | afirmación y rango; fuentes, pasajes, resultado y abstención |
| AIModelVersions, AIAnalysisResults | licencia, hash, evaluación; ejecución con features, versión, abstención y resultado calibrado solo si procede |
| StyleComparisons, WritingArtifacts | autorización y procedencia de muestras; versiones y cronología aportada, sin historial inferido |
| Rubrics, RubricCriteria, RubricEvaluations | consigna, criterio, ponderación, evidencia, puntuación propuesta y decisión docente separadas |
| DefenseQuestions, DefenseResponses | documento, tipo, pasaje base, pregunta editable, respuesta y observación autorizadas |
| ReviewCases, CaseComments, CaseDecisions, CaseAppeals | responsables, estado, comentario, decisión anterior/nueva, razón, actor y fecha |
| Reports | auditoría, revisión, snapshot de hallazgos/decisiones, hash del PDF y object_key |
| Integrations, ExternalMappings | proveedor, URL aprobada, referencia de secreto; UNIQUE(tenant,integration,type,external_id) |
| Webhooks, WebhookDeliveries | destino aprobado, referencia de clave, evento, intento, firma/versionado y respuesta acotada |
| AuditEvents, QuotaReservations, IdempotencyKeys | actividad sin texto privado, reserva atómica, clave ligada al actor/ruta/hash y expiración |

## Integridad

FK compuestas (institution_id,parent_id) referencian UNIQUE(institution_id,id) del padre; un UUID existente no basta para vincular objetos. CHECK para tamaños y contadores no negativos, rangos end > start, coseno entre -1 y 1, fecha de expiración posterior a emisión. Pesos de rúbrica suman 100 al publicar mediante validación transaccional. Decisiones y eventos son anexados, no se sobrescriben. Ningún estado de revisión equivale a culpabilidad automatizada.

Hashes de documentos no son únicos globales: duplicación se detecta dentro de la institución y se decide por política. No revelar existencia de un hash en otro tenant. Original se deduplica físicamente solo con esquema que no filtre información y permita borrado independiente; inicialmente no deduplicar almacenamiento entre tenants.

## Aislamiento

RLS habilitada y forzada para tablas tenant; rol de aplicación sin BYPASSRLS ni propiedad de tablas. SET LOCAL de tenant dentro de cada transacción, nunca configuración persistente del pool. Worker resuelve tenant desde el job autorizado y aplica el mismo contexto. Filtrado explícito en servicios además de RLS. Informes, índices vectoriales, cachés, logs y URLs de archivos preservan el tenant. Pruebas usan el rol real de ejecución, no el dueño de migraciones.

## Índices y migraciones

Índices (tenant,created_at,id), (tenant,status), (tenant,sha256), (tenant,assignment_id), (tenant,audit_id), outbox pendiente parcial y jobs por lease/status. UNIQUE en claves de idempotencia por tenant/actor/ruta/clave; misma clave con hash distinto devuelve conflicto. Alembic administra cambios revisados; migración inicial en Fase 1, sin SQL ejecutado en Fase 0. Cambiar dimensión de embeddings crea nueva colección/tabla versionada: no mezclar vectores de distintos modelos. HNSW se habilita tras medir recuperación y aislamiento.

## Retención

Borrado lógico controla acceso inmediatamente; tarea de purga elimina archivos, snapshots privados, vectores y derivados con registro verificable. Suspender purga por retención legal autorizada. Backups cifrados caducan según política; restauración reaplica tombstones antes de abrir servicio. Auditoría de seguridad retiene solo metadatos mínimos según contrato. Un informe conserva la versión de evidencia hasta que su política exija eliminarla; no crear copias permanentes sin base legal.
