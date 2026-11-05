# Fase 6 — Bibliografía local y adaptación de proveedores

## Estado real

El flujo local está implementado: extrae candidatos sobre documentos privados ya procesados, ejecuta trabajos durables y muestra evidencia verificable. La integración remota cuenta con adaptadores y pruebas de contrato, pero **no se ha validado una consulta real exitosa a Crossref u OpenAlex**: ambos orígenes fueron rechazados/no accesibles con la política actual. Esa puerta de fase 6 queda pendiente. No se ha activado Hugging Face ni inferencia semántica y no se ha iniciado la fase 7.

## Extracción y cobertura local

Reconoce encabezados de referencias/bibliografía en español e inglés y finaliza ante anexos/agradecimientos reconocidos. Identifica entradas numeradas y candidatos APA de autor (año), continuaciones, DOI canónicos y duplicados de DOI/texto. Si falta encabezado, muestra únicamente menciones de DOI y declara resultado parcial; no las presenta como referencias bibliográficas confirmadas.

Busca citas numéricas y autor-año en el texto anterior a la bibliografía. Una cita no emparejada y una referencia sin cita reconocida se etiquetan como candidatos, no como ausencia demostrada. Patrones complejos, estilos no compatibles, abreviaturas, listas de autores, títulos con puntuación y saltos de línea pueden requerir revisión. No hay un modelo lingüístico ni inferencia de editorial o citas multilingües.

Las evidencias conservan fragmento, página/párrafo, rangos originales en puntos de código Unicode, texto y SHA-256 de pasaje/fragmento. Páginas TXT siguen siendo secciones form-feed de extracción. Máximo 500 000 caracteres de texto, 200 referencias, 8192 caracteres por referencia, 500 candidatos de cita y 50 tramos por evidencia. Las citas visibles se abrevian a 2000 caracteres con bandera explícita; no reemplazan el original.

## Metadatos externos

Solo DOI, nunca texto completo, se transmite con consentimiento. No se aceptan URL arbitrarias ni se siguen redirecciones. Proveedores fijos api.crossref.org/api.openalex.org, HTTPS con verificación TLS y sin bypass de política. Un proceso hijo recibe solo el URL generado y variables de proxy/CA necesarias, sin credenciales de base de datos; timeout total seis segundos y respuesta máxima 256 KiB. Rate limit compartido de una solicitud por segundo/proveedor; ante 429, acceso rechazado o indisponibilidad se detienen las demás consultas de ese proveedor en la ejecución. No hay reintentos automáticos y Retry-After se registra acotado; límites/cuotas reales del servicio siguen pendientes de validación. Diez DOI únicos y dos proveedores por ejecución, con presupuesto temporal y 8 MiB de evidencia total.

La operación requiere habilitación del servidor, permiso institucional administrado y opt-in por ejecución. OpenAlex requiere clave configurada; no se inventa acceso gratuito ni se imprime esa clave. El worker revalida permisos y consentimiento antes de cada lookup habilitado, y permiso documental antes de persistir. Revocar permiso institucional cancela trabajos externos pendientes/en curso; los resultados tardíos no se publican. Las respuestas ya obtenidas bajo consentimiento anterior no se borran automáticamente al cambiar la política; el borrado documental sí elimina toda evidencia derivada.

Solo una respuesta 200 con esquema compatible y DOI coincidente produce metadatos recuperados. Se guardan respuesta original, SHA-256 y fecha; cuerpos de error o credenciales no se conservan; una respuesta que reproduce la clave configurada se rechaza. Título/año/publicación se comparan por reglas explícitas de texto, primer autor solo como coincidencia parcial, y campos no extraídos quedan sin comparar. Diferencias no son acusaciones. Metadata valida un registro, no el artículo completo ni sus afirmaciones.

## Durabilidad, permisos y vista

0006_bibliography crea runs/jobs con RLS forzada, FK por institución, leases y recuperación de hasta tres intentos. Creación idempotente por clave/solicitante, cancelación y privacidad por documento y solicitante/rol. Eliminar el documento invalida la revisión y limpia snapshots, resultados y nombres inmediatamente. Listados filtran antes de paginar.

Bibliografía aparece en navegación y en cada documento listo. Muestra candidatos, duplicados, estado de citas, cobertura externa, diferencias y procedencia; exporta JSON privado. La consulta remota aparece deshabilitada cuando faltan permisos/configuración. No hay decisiones académicas automáticas ni fuentes inventadas.

## Verificación

[Manifiesto y límites de la validación](validation/phase6/README.md). Pruebas de extracción, Unicode/hashes, contratos de metadatos, errores y límites, roles/tenant, idempotencia, revocación, cancelación durante consulta, recuperación de leases y transporte de host fijo. Fixtures de JSON externos se usan solo en aid_test; no constituyen consultas reales exitosas.

No se acreditan precisión académica general, verificación en línea, comparación de referencias sin DOI o comportamiento de APIs fuera de los contratos probados. Los límites de OCR, antivirus, contención completa del filesystem, Windows/WSL2 y producción de fases anteriores persisten. No hay nuevas dependencias ni GPU.
