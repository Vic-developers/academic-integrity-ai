# Fase 5 — Infraestructura vectorial sin Hugging Face

El usuario autorizó continuar sin habilitar ese origen. Se respeta esa elección: no se modifica la política de red, no se descarga ningún modelo, no se instala ONNX y no se vuelve a pedir acceso. La parte semántica que depende de un modelo real permanece pospuesta. Esta entrega completa el almacenamiento y la recuperación matemática independientes del modelo, no declara terminada la fase 5 completa.

## Implementación

`semantic_vectors` guarda vectores unitarios de 384 dimensiones con institución, versión, fragmento, model_key, chunker_version, rango original, SHA-256 del pasaje y del fragmento. Las FK compuestas impiden asociar un fragmento a otra institución o versión. La RLS está habilitada y forzada. La norma, dimensión, hashes y rangos también tienen controles de base de datos.

Las primitivas internas de escritura requieren documentos legibles con extracción terminada/parcial, rangos Unicode válidos de hasta 4096 caracteres y al menos ocho palabras. Rechazan ceros, booleanos, NaN/infinito, desbordamientos y dimensiones incorrectas. Normalizan y canonizan float32 para pgvector. La clave de caché incorpora modelo, chunker, fragmento y offsets; una segunda escritura equivalente es idempotente, mientras que cambiar un vector de esa identidad produce 409. El bloqueo del documento serializa escrituras concurrentes y borrado.

La recuperación usa `<=>` de pgvector para coseno exacto. Revalida todas las fuentes seleccionadas y filtra institución, versiones elegidas, modelo, chunker y permisos documentales antes de ordenar y aplicar top-k. Límite de 20 fuentes y top-k 1–20; hasta 200 pasajes por versión/modelo/chunker. Un cambio de texto/hash invalida la lectura de caché. No se usa ANN ni se promete rendimiento sobre un repositorio institucional completo.

Los candidatos devuelven offsets, pasaje original, página/párrafo, versiones/hashes y coseno numérico. No son hallazgos: su interpretación explícita es `numeric_vector_candidate_not_a_verified_paraphrase`. Un coseno no constituye probabilidad de plagio ni prueba de paráfrasis.

## Privacidad y activación

Borrar un documento elimina sus vectores dentro de la transacción de revocación, antes de que el worker borre el archivo. Eliminar fragmentos por purge o reextracción elimina los vectores por cascada. Una revocación de lectura impide recuperarlos aunque todavía estén almacenados.

No se exponen rutas HTTP para escribir/buscar vectores, no hay job semántico ni indexación automática. El repositorio no llama al encoder o instalador y no cambia `semantic_available=false`. Una futura integración debe verificar primero el modelo y evaluación y mantener la autorización del solicitante; este módulo no sustituye esos controles. La base de desarrollo queda sin vectores de prueba.

## Validación y alcance

Pruebas de PostgreSQL/pgvector reales, incluidas consultas coseno conocidas y comprobaciones de RLS, FK, selección de fuentes antes de top-k, modelo/chunker, revocación, idempotencia, conflictos, concurrencia, offsets Unicode, corrupción, presupuestos y borrado. Los datos y vectores son fixtures técnicos de aid_test; no simulan un modelo ni generan resultados en la interfaz.

[Manifiesto de comprobaciones](validation/phase5-vector/checks.json) y [protocolo](validation/phase5-vector/README.md). Se conservan las regresiones de autenticación/documentos/literal/PDF y se comprueba el stack real con la migración 0005_vector. No hay nuevas dependencias Python/Node. Windows/WSL2 y producción siguen sin probarse.

Permanece pendiente: obtener por una vía autorizada un modelo con licencia/revisión/hashes, resolver su runtime CPU, medir inferencia, calibrar/evaluar por idioma y dominio, y conectar jobs, pgvector y evidencias semánticas. Puede realizarse con artefactos locales verificados en el futuro, sin conexión de la aplicación a Hugging Face. No se ha comenzado la fase 6.
