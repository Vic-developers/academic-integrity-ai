# Fase 7 — Afirmaciones y evidencia local con evaluación humana

## Estado real

Se implementa la parte local de la fase 7: extracción heurística, recuperación léxica en documentos explícitamente seleccionados y clasificación humana trazable. **La clasificación automática de respaldo/contradicción y la recuperación de artículos externos siguen pendientes.** No se ha habilitado Hugging Face, un modelo NLI ni una API externa. No se inicia la fase 8.

La existencia de un DOI o de palabras compartidas no acredita una afirmación. Todas las candidatas comienzan sin evaluar, incluso ante una coincidencia literal o una negación. Los cinco estados académicos (`supported`, `contradicted`, `partially_supported`, `not_verifiable`, `insufficient_source`) representan decisiones de una persona, con motivo y actor registrados. `unreviewed` permite dejar o devolver una afirmación sin decisión.

## Extracción y recuperación

El motor local reconoce oraciones de al menos ocho palabras con cifras o señales verbales acotadas en español/inglés. Conserva decimales y posiciones originales Unicode; excluye preguntas reconocidas y el apartado bibliográfico. Se pueden añadir intervalos manualmente para corregir omisiones. Las citas APA/numéricas reutilizan el extractor local de fase 6 como asociaciones candidatas; la correspondencia entre referencia y fuente seleccionada requiere revisión.

Busca hasta tres pasajes por candidata con al menos tres términos compartidos, sin puntuaciones de certeza. Trabaja exclusivamente sobre versiones de documentos autorizados elegidos al crear la revisión. No descarga artículos ni interpreta negaciones, causalidad, metodología, calidad científica o contexto disciplinar.

Límites por trabajo: veinte fuentes, un millón de puntos de código combinados, cien afirmaciones incluidas las manuales, cinco mil pasajes indexados, doscientos mil accesos al índice y 2000 puntos de código por afirmación/pasaje. El contexto bibliográfico tiene presupuesto independiente de 500 000 caracteres; excederlo omite ese contexto y declara parcialidad. La evidencia calculada no supera 4 MiB. Límites y extracciones parciales se presentan explícitamente; ausencia de candidato nunca demuestra falta de respaldo.

## Revisión y trazabilidad

La pantalla `/afirmaciones` permite elegir principal y fuentes, paginar documentos y consultar revisiones anteriores. El resultado muestra citas originales, página/párrafo, rangos Unicode, versiones, SHA-256 y sugerencias léxicas. El evaluador puede adjuntar sugerencias o seleccionar otro intervalo del texto original, con índices en puntos de código y vista previa. Puede agregar una afirmación omitida. No hay fuentes preseleccionadas ni procedencia inventada.

Respaldada, contradicha y respaldo parcial requieren al menos un pasaje de una fuente seleccionada; todos los cambios requieren un motivo de diez caracteres como mínimo. El servidor vuelve a leer el intervalo y valida sus hashes, versión y permisos; no acepta texto de evidencia aportado por el cliente. Estudiantes pueden consultar sus revisiones pero no evaluar ni añadir selecciones manuales. Historial: hasta cincuenta revisiones y 256 KiB por afirmación, con actor, fecha, decisión, motivo y pasajes originales. Exportación JSON privada con historial completo.

El control de revisión optimista devuelve 409 ante cambios concurrentes. La pantalla mantiene el borrador y exige una acción explícita para usar la revisión actual. La clasificación se identifica siempre como humana, no como verificación automática de verdad ni prueba de plagio.

## Persistencia y permisos

La migración `0007_claims` añade `claim_runs`, `claim_sources`, `claims`, `claim_jobs`, con RLS forzada y FK compuestas institucionales. Trabajos con lease de 120 segundos, token y hasta tres intentos; permisos revalidados antes y después del cálculo, cancelación y rechazo de resultados tardíos. Idempotencia por solicitante/clave/alcance. Listados filtran todas las fuentes antes de paginar.

Borrar principal o fuente invalida la revisión, elimina afirmaciones e historiales y limpia snapshots privados; revocar acceso impide lectura y publicación. Se conserva el sistema de sesiones, CSRF, origen, cuerpos de 64 KiB y límites de frecuencia. No hay nuevas dependencias ni uso de GPU.

## Verificación y límites pendientes

La verificación real se registra en [el manifiesto de fase 7](validation/phase7/README.md). Las pruebas usan textos sintéticos explícitos y bases aisladas; verifican comportamiento, permisos y procedencia, sin medir precisión científica general. Persisten los pendientes de fases anteriores: inferencia/calibración semántica, proveedores remotos reales, OCR, antivirus, contención completa del filesystem del parser y validación Windows/producción.
