# Fase 4 — Visor de evidencias y revisión humana

## Corrección posterior del PDF

El visor aplica la transformación real de PDF.js a las cajas originales y admite las cuatro rotaciones, CropBox, orígenes desplazados y UserUnit. Conserva compatibilidad con versiones ya extraídas; solo omite el overlay cuando la referencia o los caracteres no son verificables. [Verificación](validation/pdf-correction/README.md).

El push previo autorizado quedó verificado en origin/work, commit 30e05a4. Esta fase se implementa después de ese push; no se publica automáticamente su nuevo commit.

## Comportamiento

Desde el resultado de una comparación, Abrir visor de evidencias presenta el documento principal y la fuente institucional lado a lado, o apilados en móvil. Las coincidencias conservan sus rangos en puntos de código del texto original, página, párrafo y oraciones. En TXT las páginas son secciones delimitadas por form feed, según la advertencia de extracción, no páginas impresas. DOCX usa su estructura extraída, sin prometer paginación de Word. Las versiones, SHA-256, consulta y autor declarado en metadatos cuando existe quedan visibles. No hay fuentes web verificadas ni URL inventadas.

El backend recupera únicamente el fragmento solicitado de la versión ligada al hallazgo y verifica hashes de fragmento y rango. El navegador verifica SHA-256 de nuevo antes de dibujar. Usa Array.from para convertir puntos de código a cortes JavaScript; no aplica offsets normalizados sobre texto original. La segmentación por todas las fronteras conserva solapamientos sin anidar marcas ni duplicar palabras. Cada marca enlaza al hallazgo; el selector permite elegir entre fuentes superpuestas.

La navegación cubre coincidencias y fragmentos de una misma coincidencia, incluidos saltos de página. Los filtros por fuente y estado y los marcadores temporales permiten ordenar la revisión. Los marcadores se guardan solo en memoria del visor durante esa sesión; no se presentan como anotaciones institucionales persistidas. El texto puede seleccionarse y ampliarse.

PDF conserva el canvas del original y superpone cajas de caracteres, sin modificar el archivo. Solo dibuja geometría si la secuencia de caracteres es fiable, la caja es válida y la referencia PDF.js coincide con la página extraída sin rotación ni recorte. No se amplía una caja de palabra para adivinar caracteres. Si falta geometría o existe rotación/recorte incompatible se declara la limitación y se conserva el resaltado verificable en el texto extraído. Zoom y páginas actualizan o retiran las cajas; volver a la página recupera el resaltado. En esta versión no se ofrece selección textual nativa dentro del canvas; el texto accesible y seleccionable aparece debajo.

## Revisión humana

Un evaluador autorizado puede registrar pendiente, revisado, justificado, descartado o coincidencia confirmada, con motivo obligatorio y valoración separada de citación (pendiente, correcta, ausente, incompleta). Confirmar valida una coincidencia textual, no una infracción. Estudiantes no pueden guardar revisiones, aunque puedan leer sus propios documentos/auditorías.

Cada cambio conserva revisión incremental, actor, fecha, motivo y valoración; el cliente envía expected_revision y recibe 409 si otro cambio ganó. El formulario conserva la revisión que abrió y el motivo escrito; una actualización de otra pestaña no cambia silenciosamente esa revisión ni borra el borrador. Un conflicto exige leer el historial y cargar explícitamente el estado actual. Máximo 100 revisiones por hallazgo y 2000 caracteres por motivo. Color rojo identifica coincidencia textual, verde justificación y gris descarte, siempre acompañados de etiquetas; no expresa culpabilidad. Se permite exportar JSON real con versiones, hashes, evidencia y revisión. Informes PDF, expedientes y apelaciones corresponden a fases futuras.

## Seguridad y alcance

Todas las rutas del visor, original y exportación revalidan principal y todas las fuentes de la auditoría. No aceptan rutas de archivo ni versiones arbitrarias. Retirada de fuentes impide acceso y borra los derivados según Fase 3. Revisión sigue el orden de locks documental/auditoría/hallazgo. Los cuerpos POST de auditoría y revisión se limitan a 64 KiB. El visor vuelve a consultar permisos cada 10 segundos mientras está abierto y oculta datos si recibe un error; datos ya entregados a un usuario autorizado no pueden retirarse de una copia externa.

0004_review añade revisión e historial al hallazgo existente, bajo su RLS y FK. No se cambian migraciones históricas, dependencias, motor literal ni límites de extracción.

## Verificación

Pruebas backend de rangos Unicode, hashes, versión/original, cajas de caracteres, rechazo de mapas alterados, revisión, conflictos, rol estudiantil, borrado y exportación; regresiones de fases anteriores. Pruebas de navegador con documentos reales sintéticos: solapamientos, DOCX, cambio de fragmento, filtros/marcadores, revisión persistida, móvil, PDF, zoom, píxeles de glifos dentro de cajas, retorno de página, rotación y mapa alterado. Resultados observados: [validación](validation/phase4/README.md).

Se mantiene la limitación de lectura PDF compleja y extracción/OCR de Fase 2. No se acredita precisión geométrica de todo PDF posible ni validez académica general. Windows/WSL2, producción, antivirus y contención completa del filesystem siguen pendientes. Fase 5 no iniciada; requiere autorización.
