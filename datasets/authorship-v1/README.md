# Corpus propio de autoría v1 — preparación de fuentes reales

La solicitud actual exige un corpus humano/IA real, modelo propio, evaluación independiente y calibración; los patrones técnicos de fase 8 no son admisibles para entrenar ese modelo. `sources.json` registra fuentes examinadas y su estado observado, **no un corpus ya construido**. Actualmente hay cero muestras calificadas y ningún modelo real entrenado/calibrado disponible para inferencia.

Se localizó la referencia del equipo de investigación de MULTITuDE v3 en [Multilingual-MGT-AA](https://github.com/MLNTeam-Unical/Multilingual-MGT-AA), que remite a [Zenodo 15519413](https://zenodo.org/records/15519413). El acceso al registro falló (`URLError`); zenodo.org no está en la política de hosts autorizados del entorno. No se habilitó Hugging Face, se alteró el proxy ni se buscó eludir el bloqueo. La licencia y el esquema de los archivos de ese registro siguen sin verificar.

Se encontró una copia pública de AuTexTification en un repositorio de participantes. Se comprobó que el archivo contiene datos TSV en español/inglés, pero no se confirmó una licencia de reutilización de esos datos. No se entrenó con ella, no se redistribuye el archivo y no se interpreta una licencia de software de los evaluadores como permiso sobre los textos.

## Construcción que falta completar

1. Obtener una fuente accesible con licencia de datos identificada y uso de entrenamiento/evaluación autorizado; conservar URL, versión, licencia original y SHA-256 del archivo.
2. Auditar etiquetas humanas/IA y procedencia. No generar texto y etiquetarlo como humano. Material generado por IA debe conservar generador, versión y consigna; no puede sustituir la clase humana.
3. Curar muestras españolas representativas y documentar dominios, longitudes, edición, textos mixtos y limitaciones. No reutilizar documentos institucionales sin permiso específico.
4. Reservar train/validation/calibration/test por documento, autor, fuente y consigna antes de fragmentar; registrar exclusiones y duplicados. Si el dataset no identifica autores o fuentes, declarar esa limitación y no inventar grupos independientes.
5. Convertir el corpus autorizado al esquema de [investigación](../../evaluation/experimental-ai-v1/README.md), entrenar en CPU y calibrar solo con calibration. Evaluar test intacto con FPR/intervalos, Brier/ECE y desgloses por dominio, idioma, extensión y generador no visto.
6. Definir el alcance y los límites de publicación con los resultados reales; conservar abstención fuera del alcance validado. Un ajuste numérico de Platt sobre patrones de prueba no satisface esta puerta.

La aprobación de acceso de red no acredita derechos sobre datos ni calidad del modelo. Desarrollar un corpus propio significa recopilar y documentar material de procedencia real; no permite fabricar testimonios de escritura humana. La publicación de probabilidades de autoría sigue pendiente de estos resultados, no de un interruptor que habilite cifras arbitrarias.

## Compilador del corpus propio

`scripts/build_authorship_corpus.py --collection /ruta/privada/collection.json --output /ruta/privada/corpus.json` compila exclusivamente textos `.txt` reales aportados dentro de la carpeta de colección y con SHA-256 esperado. Rechaza rutas externas, hashes alterados, fuentes sin derechos declarados y patrones técnicos; no genera muestras humanas/IA. Escribe un archivo nuevo privado, sin sobrescribir.

La colección usa los campos del esquema de corpus de investigación (dataset_id, license, authorization_reference, annotation_protocol, training_allowed, evaluation_allowed, personal_data_reviewed), `purpose: research`, `synthetic_patterns_allowed: false`, `samples` y `source_catalog`. Cada muestra conserva sus identificadores/grupos, etiqueta/split y procedencia, y reemplaza `text` por `text_path` relativo y `text_sha256`. Cada source_id exige un registro en source_catalog con training_allowed/evaluation_allowed/rights_reviewed verdaderos, kind publicado humano (`published_human`), generación registrada (`recorded_ai_generation`) o dataset curado (`curated_human_ai_dataset`), y referencias license_reference/permission_reference/label_provenance. Son declaraciones auditables del curador, no verificaciones legales automáticas.

Después de compilar: `python scripts/train_experimental_ai.py --corpus /ruta/privada/corpus.json --output /ruta/privada/experimentos`. El comando de entrenamiento rechaza por defecto los patrones técnicos de fase 8. Construir, entrenar o ajustar una calibración no activa por sí solo un detector ni acredita una probabilidad sobre una persona.
