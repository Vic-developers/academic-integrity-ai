# Fase 9 — Forense documental y comparación descriptiva de estilo

## Resultado y límites

Se implementa observación de metadatos, caracteres y propiedades explícitas de formato, con evidencia original verificable, y comparación descriptiva entre muestras autorizadas y declaradas comparables del mismo estudiante. No se infiere identidad, intención de ocultación, uso de IA o conducta indebida a partir de estos datos. No se reconstruye un historial de edición que el archivo no contiene. No se inicia la fase 10.

La solicitud adicional de probabilidades de autoría requiere un modelo propio entrenado/evaluado/calibrado con corpus real. Se registró la búsqueda de fuentes en [corpus propio v1](../datasets/authorship-v1/README.md). No se entrenó con la copia de datos sin licencia verificada ni se convirtió el ensayo sintético anterior en un detector. El acceso al registro de MULTITuDE en Zenodo falló y ese dominio no está autorizado por la política de red actual. **Probabilidades de autoría siguen pendientes de obtener datos autorizados y evaluar/calibrar el modelo real**. Las observaciones forenses y las diferencias de estilo no sirven como sustituto de esa probabilidad.

## Forense observable

El análisis opera sobre fragmentos originales autorizados y metadatos de la versión: autor declarado, fechas, revisiones y software cuando están disponibles. DOCX añade Application/AppVersion del XML de propiedades acotado, propiedades explícitas hidden, color blanco y tamaño de fuente de cada run que se puede mapear. PDF conserva geometría previa y añade tamaño mínimo y color blanco observado por palabra. La extracción queda identificada con `forensic-v1`; documentos extraídos antes no se reescriben ni se presentan como libres de anomalías por no disponer de esos atributos.

Detecta categorías Unicode de formato/control, espacios inseparables, cambios NFKC de caracteres individuales y mezclas latín/griego/cirílico dentro de palabras. Cada observación conserva fragmento, página/párrafo, rango en puntos de código, texto y hashes de pasaje/fragmento. Los controles se muestran escapados para evitar engaños visuales; el JSON conserva el original para verificar el hash. Usos lingüísticos legítimos, ligaduras, abreviaturas y maquetación pueden explicar observaciones.

Color blanco no implica invisibilidad: puede haber fondo coloreado. Hidden de DOCX es una propiedad declarada, no una medición de renderizado. Fuentes de hasta dos puntos son un criterio técnico visible en el informe, no umbral científico de fraude. No se resuelven estilos heredados, modos de renderizado PDF, todas las capas, revisiones eliminadas o relaciones completas del paquete. Solo se inspeccionan intervalos de formato de hasta 2000 puntos de código; se pueden omitir runs mayores y mapas no fiables. No se atribuyen estos fenómenos automáticamente a una persona.

Fechas: solo formatos ISO sin zona y fechas PDF completas UTC reconocidas; formatos incompatibles quedan sin comparar. Una modificación anterior a creación es un contexto por revisar, no prueba de alteración deliberada. Los metadatos son editables y sus valores pueden estar truncados por el extractor. Máximo 500 000 caracteres, primeras 250 observaciones con conteo total, y cien propiedades escalares; no incluye en la tabla la geometría por página. No se garantiza detectar todas las sustituciones Unicode o textos ocultos.

## Autorización y comparación de estilo

El evaluador registra por versión: autorización activa, referencia de consentimiento, procedencia, idioma, dominio, género, fecha documentada, motivo y si se trata de una muestra anterior de escritura verificada. Se vincula al propietario estudiante activo, no al campo Autor del archivo. La verificación es una declaración humana trazable, no una prueba automática de identidad. Historial de hasta veinte revisiones y 64 KiB, con actor/fecha y control optimista; conflictos devuelven 409.

Comparación de un trabajo con dos a cinco documentos anteriores: mismo estudiante activo, permiso de lectura sobre todos, autorizaciones activas y revisiones vigentes. Las fuentes requieren verificación humana explícita y fecha anterior al trabajo. Idioma/dominio/género declarados deben coincidir. Requiere extracciones completas, cien tokens mínimos por muestra y textos no duplicados. Dos muestras/cien tokens son mínimos técnicos, no suficiencia estadística ni validación científica de un perfil.

Se comparan las ocho medidas observables de fase 8 contra mediana/rango de las muestras y se muestran diferencias numéricas, versiones, hashes y registros de autorización. Sin puntuación global, probabilidad de autoría, clasificación de identidad ni conclusión de uso de IA. No hay análisis sintáctico/semántico aprendido; tema, longitud, edición y extracción pueden explicar cambios. Presupuesto combinado 500 000 caracteres. Revocar autorización, cambiar propietario, desactivar estudiante o borrar/restringir una muestra impide nuevas comparaciones; resultados no se persisten en el servidor y la pantalla revalida periódicamente y los oculta ante error.

## Persistencia y seguridad

`0009_forensics`, posterior a `0007_claims` (fase 8 no añadió esquema), crea `style_attestations` con RLS forzada y FK institucionales a versión/estudiante. Solo evaluadores pueden registrar autorizaciones y comparar; estudiantes consultan observaciones de sus documentos. Las lecturas y escrituras validan permisos actuales. Bloqueos documentales en orden y revisión optimista evitan comparar autorizaciones obsoletas. El borrado limpia la autorización/historial del documento y revoca el acceso; no almacena informes derivados.

API con sesión/origen/CSRF, escrituras de hasta 64 KiB; 300 lecturas forenses y 120 comparaciones por miembro/quince minutos. La nueva pantalla `/forense` permite consultar propiedades y ubicaciones, exportar JSON, registrar autorizaciones, comparar y consultar trazabilidad. Los módulos se cargan de forma diferida. No hay dependencias nuevas, GPU, Hugging Face, OCR o antivirus añadidos.

[Contrato API](FORENSICS_API.md). [Verificación real y limitaciones](validation/phase9/README.md). Persisten los pendientes científicos de semántica, fuentes remotas y autoría, contención completa del parser, Windows y producción. La continuación de la hoja de ruta es fase 10, comparador masivo; se mantiene pendiente la solicitud de modelo/probabilidades hasta superar la puerta de datos/calibración real.
