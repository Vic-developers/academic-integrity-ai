# Fase 3 — Coincidencias literales verificables

Implementada en Linux CPU, sin GPU ni nuevas dependencias. Se comparan documentos institucionales seleccionados explícitamente y legibles por el solicitante. El índice winnowing se construye por ejecución; no existe indexación global automática.

## Comportamiento y límites

`literal-winnow-v1` usa k-gramas de 5 tokens, ventanas de 4 y mínimo de 8 palabras. Las huellas BLAKE2b proponen candidatos; la igualdad real de tokens confirma cada rango y se extiende hasta sus límites. Se aplica el normalizador documental NFKC/casefold con mapa v1: mayúsculas y espacios pueden diferir; la puntuación interior debe coincidir. Los rangos pueden cruzar fragmentos y páginas.

Cada hallazgo contiene rangos originales en puntos de código, texto, hash, versión de documento/extractor/motor y localizadores disponibles. Los fragmentos de cita se limitan a 2000 caracteres y los localizadores a 200 elementos, con truncamiento explícito. La igualdad del texto bruto queda indeterminada si está truncado. La revisión humana y la valoración de citas permanecen pendientes. Ninguna coincidencia demuestra plagio.

El resumen cuenta la unión de posiciones de palabras del documento principal, sin duplicar solapamientos ni fuentes. Su denominador es el texto extraído: no mide originalidad, probabilidad de plagio ni cobertura de páginas sin OCR.

Límites por ejecución: 20 fuentes, un millón de caracteres normalizados combinados, 50 000 pares semilla, dos millones de comparaciones de tokens, 500 hallazgos y 8 MiB de evidencia persistida. Los límites, las extracciones incompletas y los textos demasiado cortos producen cobertura parcial explícita. El proceso hijo tiene límites de recursos y 40 segundos de plazo.

## Web y permisos

Existe interfaz SearchProvider y planificación de consultas. No hay proveedor web autorizado/configurado: se registran cero consultas enviadas y cero fuentes verificadas. Solicitar web produce resultado parcial aunque la comparación local termine. Un snippet nunca se convierte en evidencia verificada; no se descargan URL arbitrarias ni se eluden permisos de sitios.

Se comprueban permisos al crear, ejecutar, persistir y consultar. Todas las fuentes deben seguir siendo accesibles. Listados filtran antes de paginar. Eliminar un documento invalida auditorías relacionadas, borra hallazgos y datos derivados y cancela sus trabajos. RLS forzada y FK compuestas protegen las cuatro tablas nuevas. Jobs con leases, tokens de reclamación y recuperación acotada; Idempotency-Key evita duplicados concurrentes.

## Validación real

65 pruebas backend: algoritmo, colisiones, Unicode, evidencia, permisos, aislamiento, revocación, borrado, cancelación, idempotencia concurrente y migraciones; se conservan las regresiones de fases anteriores. Compilación TypeScript estricta y contenedores reales. El cierre de navegador y procedencia se registra en [validación](validation/phase3/README.md).

El corpus técnico sintético de 201 casos pasó el umbral del protocolo. No representa escritura académica ni mide cobertura de Internet, detección de plagio o rendimiento de producción. Véase [evaluación reproducible](../evaluation/literal-v1/README.md).

Persisten los límites de Fase 2: sin OCR, antivirus ni contención completa del filesystem del parser; Windows/WSL2 y producción no probados. No hay motor semántico, detector de IA, resaltado exacto interactivo, revisión de decisiones ni informes. La fase 4 requiere autorización. No se hace push.
