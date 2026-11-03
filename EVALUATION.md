# Evaluación y pruebas

## Evidencia actual

Fase 0: inspección del entorno, consulta TLS de metadatos y fuentes oficiales, revisión documental y enlaces locales. Cero pruebas de aplicación ejecutadas porque no existe implementación. No hay métricas de precisión, tiempos de inferencia ni capacidad concurrente medidas. Los objetivos siguientes son criterios de aceptación propuestos, no resultados.

## Protocolo científico

Versionar dataset con hashes, origen, licencia, autorización, idioma, dominio, anotadores y reglas. Reservar test antes de optimizar. Dividir por documento/autor/fuente; nunca distribuir fragmentos de un mismo original entre entrenamiento y test. Doble anotación independiente, adjudicación y acuerdo entre evaluadores para categorías interpretativas. Fijar semillas, herramientas, modelo, configuración y hardware. Publicar conteos, exclusiones, intervalos de confianza y fallos; no sustituir datos reales por datos sintéticos fuera de las pruebas técnicas.

| Motor | Evaluación |
|---|---|
| Literal | Precisión/recall de rangos a nivel token, fuente y documento; falsos positivos en citas/bibliografía; exactitud de ubicación |
| Semántico | Recall@k y precisión de recuperación separados de precisión de hallazgos; pares temáticos negativos; español y pares interlingües |
| IA | F1, precision, recall, FPR con intervalos, Brier/ECE y curvas de calibración; por dominio, longitud, edición y generador; cobertura de abstención |
| Referencias | Extracción, resolución DOI, correspondencia de metadatos y cobertura por proveedor, incluyendo fallos de red |
| Afirmaciones | Etiquetas humanas y pasajes de respaldo/contradicción; exactitud y abstención con fuentes inaccesibles |
| Forense/estilo | Propiedades verificables contra originales y variación por muestras autorizadas; no métricas de autoría inventadas |

Objetivo inicial literal: precisión ≥0,98 y recall ≥0,95 en corpus controlado definido antes de medir. Umbral de recuperación semántica y FPR de IA no se aprueban sin corpus representativo; diseñar gate con institución y coste de error. Si no se satisface, mantener experimental/no disponible. No usar un agregado global para ocultar fallos en español.

## Plan automatizado

- Unitarias: Unicode, tokenización, fingerprints con colisiones, unión de solapes, mapeo y serialización UTF-16, reglas de estados y firmas.
- Integración con PostgreSQL/pgvector real: RLS con rol restringido, transacciones, cuotas, idempotencia, migraciones, filtros vectoriales y aislamiento por tenant.
- Documental: TXT UTF-8, DOCX con tablas, encabezados y runs fragmentados, PDF en columnas, ligaduras, páginas giradas, PDFs corruptos/encriptados y escaneados. OCR debe declarar baja fiabilidad; no colorear geometría no validada.
- Worker: entrega duplicada, caída entre escritura y confirmación, Redis perdido, outbox pendiente, timeout, cancelación y recuperación por lease.
- Proveedores: fixtures solo en pruebas; ensayos reales opt-in registran respuesta, tiempo y cuota. Diferenciar indisponible de no localizado.
- E2E: login → carga → auditoría real de dos documentos de prueba → coincidencia → resaltado → decisión → informe, permisos de alumno y otro tenant.
- Seguridad: SSRF con redirección y rebinding, ZIP bombs acotadas, traversal, XSS, CSRF, revocación, enumeración y borrado.
- Accesibilidad: teclado completo, foco, etiquetas, contraste y lector de pantalla; WCAG 2.2 AA como objetivo.

## Localización crítica

Para cada coincidencia se reconstruye texto desde rangos originales y se compara con evidencia. Casos con emoji, combinaciones diacríticas, ß/casefold, CRLF, espacios, guiones de salto, ligaduras, párrafos y varias páginas. Round-trip Python code points ↔ UTF-16 probado. PDF compara caja y palabra de una referencia anotada; objetivo cero desplazamientos silenciosos en fixtures. Si no se puede mapear, no dibujar una caja engañosa.

## Operación

Medir p50/p95, errores, RAM máxima y cola con corpus declarado de tamaños e idiomas, en hardware registrado. Objetivos iniciales: API de metadatos p95 <500 ms con 20 usuarios activos; los jobs asíncronos se miden aparte. No son garantías SLA. Ensayar restore de backup, purga y reanudación de colas. CI separa pruebas rápidas de evaluaciones pesadas y conserva reportes del run actual; ningún cero-tests se considera validación.
