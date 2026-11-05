# Interfaces y visualizador de evidencias

## Estado actual — Fase 3

Comparaciones permite escoger principal y fuentes, consultar estado real y abrir citas originales con rangos/versiones. Cobertura web separada muestra indisponibilidad y cero consultas. La pantalla requiere revisión humana; no expone un porcentaje de culpabilidad. Resaltado exacto y decisiones siguen en fase 4/futuras.


## Navegación y pantallas

Login y recuperación; espacio institucional con sidebar por permisos: Dashboard, Documentos, Nueva auditoría, Historial, Resultados, Visor, Comparador, Referencias, Rúbricas, Defensa, Casos, Informes, Estadísticas, Instituciones, Usuarios, Modelos, Configuración, Integraciones y Actividad. Una ruta oculta en la UI no sustituye autorización servidor. React Router organiza rutas; TanStack Query controla caché por institución/usuario y la vacía al cambiar sesión/tenant. React Hook Form y Zod validan formularios; el servidor revalida siempre.

Dashboard vacío muestra cero y explicación de primer paso, no métricas de ejemplo. Datos reales desde BD; filtros por período, curso, estado, docente y categoría. Nueva auditoría selecciona versiones, alcance autorizado y motores con disponibilidad y coste/cuota visible. Historial muestra resultados parciales y errores recuperables. Modelos muestra revisión, límites y estado de evaluación; ninguna confianza sin calibración. Gráficos Recharts con tabla alternativa accesible.

## Visor de dos paneles

Izquierda: documento original paginado, zoom, selección y resaltados; PDF.js para PDF y representación estructurada fiel para DOCX/TXT. Derecha: fuente, título/autor si existen, URL verificada, fecha, tipo de recuperación, fragmento/contexto y alcance de verificación. Panel de explicación incluye categoría, ubicación, comparación, citación pendiente/correcta/ausente/incompleta y estado humano. Acciones revisar, comentar, descartar, justificar, confirmar y exportar requieren permiso y motivo; confirmar es decisión de evaluador, no resultado del motor.

Lista de hallazgos navegable por teclado y filtros. Selección sincroniza ambos paneles; carga diferida de páginas conserva selección mediante IDs estables, no estado exclusivo del DOM. En móvil los paneles se alternan mediante pestañas manteniendo foco y selección. PDF sin capa textual fiable presenta limitación y texto extraído aparte.

## Coordenadas y mapas

Normalización produce secuencia normalizada y lista de segmentos con rango normalizado → uno o varios rangos originales. Cada transformación conserva origen: composición Unicode, expansión casefold, espacios, guiones y exclusiones. Una coincidencia puede corresponder a múltiples rangos y páginas; nunca usar offsets normalizados directamente en el documento original.

Offset canónico: puntos de código Unicode, inicio inclusivo y fin exclusivo. En frontend convertir explícitamente a UTF-16 para APIs JS; Python len y JavaScript length no son equivalentes con emoji. Por fragmento: página, párrafo, oración, texto original inmutable y versión del extractor. DOCX conserva parte OOXML, párrafo, runs y tablas; no prometer geometría de página de Word sin motor de renderizado compatible. Mostrar vista estructurada y declarar esa limitación.

PDF conserva palabras, cajas, page box, rotación y espacio de coordenadas de extracción. Convertir mediante viewport de PDF.js por zoom/rotación; no almacenar píxeles de pantalla. OCR incorpora resolución, transformación a página y confianza; cajas no verificables no se dibujan como exactas. Pruebas de round-trip y corpus de páginas giradas/multicolumna son obligatorias.

Solapes: segmentar límites y conservar conjunto de IDs por segmento; permitir elegir evidencias superpuestas, sin ocultarlas con una sola capa. La fuente usa su propio mapa; no transferir offsets entre dos textos parecidos. Evidencia conserva hashes de versión y snapshot; si cambia contenido, el hallazgo anterior sigue anclado a su versión.

## Diseño y accesibilidad

Sistema de tokens claro/oscuro, tipografía legible y contraste WCAG 2.2 AA. Rojo = exacta; amarillo = semántica; naranja = posible paráfrasis; azul = referencia pendiente; verde = justificada; gris = descartada. Siempre etiqueta/icono y descripción: el color no expresa culpabilidad. Estados vacíos, carga, indisponibilidad y errores con acción concreta. Foco visible, botones semánticos, encabezados, live region para progreso moderado y alternativa textual a gráfico/PDF. Las 20 pantallas son diseño de producto: no están implementadas.

## Estado de Fase 1

Implementados login, recuperación, selección institucional, resumen, usuarios y actividad, tema y layout responsive. Las demás pantallas y el visualizador son diseño pendiente de fases posteriores. Las rutas de administración comprueban el rol para mostrar acciones, además de la autorización obligatoria del servidor.

## Estado de Fase 2

Documentos incluye carga por lote/arrastre, límites reales consultados, lista paginada y errores por archivo. Detalle incluye PDF original paginado/zoom o texto estructurado DOCX/TXT, normalización opcional, metadatos y descarga privada. Asignaturas incorpora actividades y matrículas. Los estados son de extracción; no hay indicadores de plagio o autoría. Los resaltados y visor comparativo siguen como diseño de Fase 4.
