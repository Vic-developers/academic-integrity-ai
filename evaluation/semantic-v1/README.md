# Protocolo semántico — Preparación de Fase 5

Estado: **no ejecutado**. El proxy rechazó Hugging Face (CONNECT 403); no se han descargado pesos, verificado licencias del artefacto concreto, generado embeddings ni medido precisión, recall, cobertura o latencia semántica. No hay umbral aprobado.

## Candidato y verificación previa

Candidato multilingüe: paraphrase-multilingual-MiniLM-L12-v2, variante ONNX cuantizada para CPU. La identidad definitiva debe incluir revisión inmutable de modelo base y conversión ONNX, SHA-256 de cada archivo, licencia declarada de ambos repositorios, tokenizer, pooling, dimensión y longitud máxima. El instalador recupera esas propiedades del origen autorizado y conserva los model cards; no confunde el identificador del candidato con aprobación.

`models/semantic-candidate.json` registra explícitamente revisión, hashes y evaluación ausentes. `scripts/prepare_semantic_model.py` fija revisiones antes de descargar y rechaza licencias no incluidas en su lista de revisión, destinos ajenos a HTTPS/Hugging Face, archivos excesivos, checksum diferente y reemplazo de una versión existente. Un candidato descargado permanece sin activar.

## Puertas para avanzar

1. Acceder al origen y verificar los artefactos/licencias. No ejecutar código remoto ni deserializar pickle; ONNX y tokenizer son datos, con pesos externos prohibidos por carga desde bytes.
2. Resolver dependencias CPU mantenidas (`onnxruntime`, `tokenizers`, `numpy`) con hashes, licencias y auditoría. El backend actual Alpine no incluye ese runtime: la integración prevista debe separar el proceso de inferencia sobre una imagen compatible con las ruedas CPU. No se ha construido ni probado esa imagen en esta preparación.
3. Comprobar contrato ONNX, dimensión, padding, atención, pooling enmascarado y normalización L2; verificar que no hay truncamiento silencioso. Medir CPU/RAM/tiempos reales, sin GPU.
4. Crear y congelar corpus autorizado antes de ajustar umbrales. Separar desarrollo, calibración y prueba por documentos/familias y dominio. Incluir paráfrasis, tema común sin reutilización, negación, cambios de cantidades y ejemplos interlingües. Conservar procedencia y etiquetas humanas; los fixtures sintéticos solo validan la mecánica.
5. Ajustar umbral solo con calibración y aplicar una vez a prueba: precisión/recall/F1 de candidatos, recuperación top-k, falsos positivos, intervalos y abstenciones por idioma/longitud. No presentar un coseno como probabilidad de plagio ni denominar paráfrasis confirmada a un tema compartido.
6. Solo después de superar la puerta experimental, integrar embeddings en pgvector con RLS y revisión del modelo, recuperación filtrada por institución y documentos autorizados antes de top-k, trabajos durables, borrado de vectores y evidencia trazable. Ampliar pruebas de API, permisos, aislamiento y navegador antes de declarar Fase 5 terminada.

No hay aprobación automática basada en modificar un booleano del manifiesto. El registro actual rechaza la activación en todos los casos mientras esta puerta no esté implementada y superada. No existe búsqueda vectorial ni motor semántico disponible en la aplicación actual.
