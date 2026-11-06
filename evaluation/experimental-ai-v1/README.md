# Protocolo de investigación de autoría experimental v1

Este directorio contiene únicamente un generador de **patrones técnicos inventados**. No es un corpus humano/IA. Sus etiquetas arbitrarias permiten verificar entrenamiento, splits, hashes y métricas; no permiten afirmar que el modelo detecta IA.

## Ensayo técnico reproducible sin red ni GPU

```bash
python evaluation/experimental-ai-v1/technical_fixture.py /ruta/privada/fixture.json
python scripts/train_experimental_ai.py --corpus /ruta/privada/fixture.json --output /ruta/privada/experimentos
```

Usar una carpeta privada fuera del repositorio para corpus reales y experimentos privados. Solo requiere biblioteca estándar de Python; no carga `.env`, SQL, pesos ni descargas. Ante errores, CLI no imprime el corpus. Una segunda ejecución sobre el mismo directorio/identidad rechaza sobrescribirlo. No hay aprobación o integración automática del clasificador: la API devuelve siempre resultado no concluyente.

## Formato de corpus autorizado

Objeto con `schema: experimental-authorship-corpus-v1`, `dataset_id`, `purpose` (`research` o `technical_fixture`), `license`, `authorization_reference`, `annotation_protocol`, `training_allowed: true`, `evaluation_allowed: true`, `personal_data_reviewed: true` y `samples`.

Cada muestra contiene:

```json
{
  "id": "identificador-de-muestra",
  "document_id": "documento-original",
  "author_id": "autor-o-grupo-de-generacion-verificado",
  "source_id": "fuente-o-coleccion",
  "prompt_id": "plantilla-o-procedencia-de-consigna",
  "language": "es",
  "domain": "dominio-declarado",
  "generator": "humano-o-modelo-version-y-configuracion",
  "provenance_reference": "registro-privado-de-origen-y-anotacion",
  "label": "human",
  "split": "train",
  "text": "Contenido autorizado de al menos diez tokens. Este bloque solo ilustra el esquema."
}
```

El ejemplo aislado no es un corpus entrenable ni un registro de autoría real. Etiquetas válidas: human, ai, mixed, edited. Splits: train, validation, calibration, test; mínimo técnico de dos muestras human y dos ai en cada uno. Mixtos/editados solo en validation/test, fuera de exactitud binaria. Reservar splits completos **antes de fragmentar**; incluir todas las variantes de un autor, documento, fuente o consigna en el mismo split. Auditar manualmente posibles duplicados, traducciones, versiones y derechos; la validación automática no acredita estos hechos por sí sola.

## Puerta científica pendiente

Antes de proponer aprobación, recopilar datos autorizados y representativos con revisión independiente de etiquetas, separación temporal y generadores no vistos. Definir por adelantado coste de falsos positivos, intervalos y tamaños suficientes por dominio/idioma/longitud; evaluar textos editados, mixtos y fuera de distribución. Añadir validación externa, revisión institucional, documentación de datos/modelo y un proceso de aprobación explícito. Una buena métrica sobre los patrones técnicos no satisface ningún criterio de este tipo.

El baseline actual usa características léxicas/de longitud y Platt en un split separado. No aprende sintaxis/semántica ni generaliza por el solo hecho de entrenar. No se reportan probabilidades personales de autoría. Las estadísticas de calibración sintéticas solo comprueban cálculos. El runtime se abstiene en todos los documentos; tampoco convierte una decisión humana previa sobre afirmaciones en una etiqueta de autoría.

Consulta [alcance de fase 8](../../docs/PHASE_8.md) y [evidencia técnica](../../docs/validation/phase8/README.md).
