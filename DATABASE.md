# Modelo de datos

## Estado de Fase 2

La migración 0002_documents añade courses, assignments, enrollments, documents, document_versions, document_fragments y document_jobs, con RLS forzada y FK compuestas. claim_document_job y fail_exhausted_document_jobs son funciones SECURITY DEFINER de uso interno con search_path fijo, privilegios revocados a PUBLIC y salida mínima. La primera migración permanece congelada.

## Estado al cierre de Fase 1

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
