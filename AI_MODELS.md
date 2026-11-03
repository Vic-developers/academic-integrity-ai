# Diseño de motores y modelos

## Coincidencia literal

Normalización versionada con mapa reversible: Unicode, espacios y comparación por mayúsculas sin perder originales. Tokenización con offsets; n-gramas y fingerprints mediante winnowing para recuperación institucional. Confirmación por secuencias de tokens y extensión de rangos sobre texto realmente recuperado. Citas y bibliografía se etiquetan/excluyen mediante política explícita conservando evidencia. La cobertura es unión de intervalos, evitando contar dos veces solapes; porcentaje de texto comparado/coincidente no implica probabilidad de plagio.

No fijar n, ventana ni longitud mínima arbitrariamente como umbrales científicos: evaluar en corpus de Fase 3. Fingerprint es índice de candidatos; colisión hash se resuelve comparando tokens reales. Comparaciones masivas reutilizan índice invertido para evitar todos los pares cuando sea posible, con medición de pérdidas de recall.

## Búsqueda web real

Proveedores enchufables con términos de uso revisados. La comparación institucional funciona sin API comercial. No existe promesa de búsqueda general de Internet gratuita y exhaustiva. Evaluar instancia propia de SearXNG solo si los buscadores subyacentes autorizan ese uso; autoalojamiento no concede permiso de scraping. Crossref/OpenAlex aportan metadatos académicos, no son buscadores de texto completo arbitrario. Se pueden registrar fuentes públicas autorizadas y colecciones abiertas como cobertura acotada.

Seleccionar fragmentos informativos con presupuesto por auditoría y excluir datos personales; consultas externas opt-in institucional. Registrar consulta, proveedor, fecha, páginas y fuentes fallidas. Recuperación separada de comparación: extracción de HTML permitido, PDFs accesibles bajo límites, URL final, hash y snapshot según licencia. Robots, términos, rate limits, Retry-After, caché y copyright deben respetarse. No saltar paywalls. Si solo hay snippet, estado extracto_no_verificado; no se computa como página comparada. Sin proveedor habilitado, motor web no_disponible y auditoría parcial si era solicitado.

## Similitud semántica

Sentence Transformers local, modelo multilingüe candidato multilingual-e5-base (revisión y licencia del artefacto pendientes de verificar) y alternativa paraphrase-multilingual-MiniLM-L12-v2 para menor memoria. No aprobado todavía ninguno. Verificar español, pares interlingües, documentos largos, prefijos requeridos por el modelo y límites de tokens. Fragmentación por oración con ventana y solape; conservar mapa al original. pgvector recupera top-k por tenant; comparación y posible reranking separado, sin confundir tema común con paráfrasis. Umbral ajustado en validación independiente, pruebas por dominio/idioma. Modelo, tokenizer, pooling, dimensión y revisión forman identidad indivisible.

## IA experimental y estilo

Primero métricas observables: diversidad léxica robusta a longitud, repetición y distribución de oraciones. Describirlas sin inferir autoría. Baseline supervisado futuro con scikit-learn; Transformers/PyTorch solo si mejora evaluación con coste justificable. Conjunto humano/IA autorizado, licencias de uso, procedencia, idioma, dominio, generador y grado de edición. Separar por autor, fuente, plantilla y documento antes de fragmentar; deduplicar entre splits. Prueba temporal y generadores no vistos, textos mixtos/editados y grupos lingüísticos.

Sin datos o calibración: resultado no concluyente, sin score de autoría. Abstención por fuera de distribución, texto corto, idioma no validado, versión no aprobada o incertidumbre. Comparación estilística requiere muestras verificadas comparables y autorización; un cambio de estilo no demuestra IA. No entrenar sobre documentos institucionales sin autorización específica.

## Bibliografía, afirmaciones y forense

DOI se extrae y normaliza, consulta Crossref/OpenAlex mediante adaptadores, compara título, autores y año conservando diferencias y respuesta original. DOI resuelto no valida todas las afirmaciones. No encontrado no significa inventado. OpenAlex puede imponer clave/cuota: revisar condiciones vigentes y declarar indisponibilidad sin inventar resultados.

Afirmaciones: identificar pasajes y fuente asociada, recuperar contenido autorizado y mostrar pasajes que sostienen la clasificación. Modelo NLI/LLM local solo tras evaluar español, contradicción y abstención; ausencia de pasaje implica no verificable. Forense registra propiedades observadas, caracteres invisibles y metadatos con limitaciones; no reconstruye historial ausente. Rúbricas y preguntas de defensa usan pasajes y revisión docente; un LLM futuro no obtiene herramientas ni acceso a secretos a partir del documento.

## Registro del modelo

Manifiesto obligatorio: identificador, revisión inmutable, SHA-256 de artefactos, licencia del modelo y datos, tokenizer, dependencias, hardware, límites de idioma/longitud, dataset de evaluación y consentimiento, métricas con intervalos, umbrales, fecha y responsable de aprobación. Cambiar modelo obliga a nueva evaluación. No hay modelos descargados, entrenados, calibrados ni aprobados en Fase 0.
