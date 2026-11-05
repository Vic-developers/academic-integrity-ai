# Fase 5 — Preparación y bloqueo de origen

## Continuación sin Hugging Face — Infraestructura vectorial

El usuario decidió continuar sin habilitar Hugging Face. La indicación histórica de habilitar el origen que aparece abajo ya no es un requisito para este trabajo: la parte de modelo se pospone. Se completó infraestructura interna de vectores sin inferencia: [continuación](PHASE_5_VECTOR.md). No se hicieron solicitudes al origen del modelo en esta continuación.

La fase 4 y la corrección del PDF se publicaron en origin/work hasta `0a8db5e8d28168d7948991e8be2a43dcb7891a21`. Las nueve pruebas de navegador incluyeron rotación 0/90/180/270, CropBox, origen desplazado y UserUnit con verificación sobre glifos reales.

La fase 5 **está iniciada, no terminada**. La consulta real a Hugging Face fue rechazada por el proxy con CONNECT 403. El instalador devolvió `model_source_network_unavailable`, código 2, sin crear artefactos parciales. La configuración actual permite registros de paquetes y GitHub, pero no ese origen ni su CDN. Es necesario habilitar `huggingface.co` y sus destinos de descarga bajo `.hf.co` y `.huggingface.co` mediante la configuración del entorno.

## Trabajo preparado

- Instalador de candidato multilingüe ONNX CPU, con revisión inmutable, SHA-256, comprobación de licencias declaradas, descargas limitadas, redirecciones restringidas y publicación atómica. No activa modelos automáticamente.
- Registro local que comprueba integridad, conjunto exacto de archivos, tamaños y rutas; rechaza enlaces simbólicos, modificaciones y activación sin evaluación.
- Clase de inferencia para evaluación offline, proveedor exclusivamente CPU, mean pooling con máscara y L2 según configuración verificada; sin descarga automática ni código remoto. **La inferencia no se ha ejecutado ni validado con un modelo real.** Las dependencias ONNX no están instaladas en el runtime del producto.
- Fragmentación con offsets originales Unicode y presupuesto del tokenizer, ventanas con solape, límites de texto/pasajes y omisiones explícitas. Se prueba con contadores técnicos inyectados, no con embeddings simulados.
- [Protocolo de evaluación y puertas pendientes](../evaluation/semantic-v1/README.md).

No se han cambiado las capacidades de la aplicación: semántica sigue no disponible. No hay vectores institucionales, trabajos semánticos, métricas de exactitud ni modelo aprobado. La recuperación pgvector y la interfaz semántica quedan pendientes de verificar primero el modelo, respetando el desarrollo por fases.

## Comprobación

Los tests nuevos verifican integridad/abstención, rechazo de rutas, redirecciones, rollback de staging, Unicode, ventanas y presupuestos. Son pruebas de preparación e integridad; no acreditan similitud semántica. El resultado real se registra en [validación](validation/phase5-preparation/checks.json). Las regresiones completas de backend se ejecutan sobre aid_test/Redis 15.

Para reanudar, habilitar el origen en la configuración de red y ejecutar:

```sh
python scripts/prepare_semantic_model.py --output-dir models/cache
```

Un resultado de descarga correcto solo habilita la evaluación posterior, no termina la fase. Los pesos quedan excluidos de Git. Windows/WSL2 y la inferencia en contenedores siguen pendientes de validación.
