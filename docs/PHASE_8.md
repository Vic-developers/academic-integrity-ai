# Fase 8 — Pipeline experimental en CPU y observaciones lingüísticas

## Estado real

El pipeline offline de corpus, entrenamiento baseline, evaluación, calibración de Platt y versionado está implementado. Se ejecutó realmente en CPU sobre 48 muestras de **patrones sintéticos con etiquetas arbitrarias**, destinadas únicamente a probar el software. No constituyen datos humanos/IA ni validación científica de un detector. Los artefactos están identificados como `technical_fixture`, `approved: false` y separados del runtime. No se habilitó Hugging Face ni se descargaron modelos o datasets.

**La puerta científica de fase 8 sigue pendiente:** no existe en el proyecto un corpus representativo autorizado y etiquetado que permita medir falsos positivos académicos, generalización y calibración de autoría. No hay clasificador aprobado, probabilidad de autoría ni activación de experimentos desde la aplicación. No se inicia fase 9.

## Observaciones disponibles

La pantalla Observaciones lingüísticas (`/indicios-ia`) permite elegir un documento autorizado y muestra conteos y estadísticas reales del texto extraído: tokens, vocabulario, oraciones, párrafos, diversidad móvil MATTR hasta ventana 50, proporción de términos únicos, repetición de trigramas, variación y media de longitud de oración, longitud media de token y puntuación por token. Conserva versión, SHA-256 de archivo/texto y versión del motor.

Normalización NFKC/casefold y tokenización Unicode de letras/números con apóstrofes internos. Segmentación por puntuación/saltos, respetando decimales; no analiza estructura sintáctica ni representaciones semánticas. Fragmentos originales unidos con dos saltos de línea. Máximo 500 000 puntos de código, aviso bajo cien tokens y ante extracción parcial. Los valores dependen de longitud, idioma, dominio, maquetación y edición; no son indicios exclusivos de IA.

El resultado de autoría es siempre `not_conclusive`, con `authorship_probability: null` y `model: null`. No se entrena sobre el documento. El módulo no compara autores ni estilos históricos. No existen semáforos acusatorios ni porcentajes de uso de IA. Las observaciones no deben ser fundamento exclusivo de una sanción.

## Corpus explícito y prevención de contaminación

Un operador proporciona un archivo JSON local, con licencia, referencia de autorización, protocolo de anotación y declaraciones explícitas de permiso de entrenamiento/evaluación y revisión de datos personales. El pipeline registra estas declaraciones; **no verifica por sí mismo su validez jurídica, representatividad o calidad de las etiquetas**. No consulta la base de datos institucional, lee `.env`, descarga datos ni solicita red.

Cada muestra declara documento, autor, fuente, plantilla/prompt, idioma, dominio, generador, procedencia, etiqueta y split. Los cuatro splits son train, validation, calibration y test. Documento/autor/fuente/prompt deben ser disjuntos entre splits; rechaza texto normalizado duplicado y cualquier secuencia compartida de ocho tokens entre splits. Esta última regla es conservadora y puede rechazar expresiones comunes; no detecta todas las paráfrasis o traducciones. Metadatos incorrectos pueden ocultar contaminación. No se acepta un valor genérico compartido de autor/prompt desconocido entre splits como prueba de independencia.

Etiquetas human/ai para entrenamiento/calibración. Datos mixtos/editados se admiten en validación/test, se contabilizan separadamente y se excluyen de la métrica binaria. Cada split requiere al menos dos muestras por clase binaria como mínimo técnico, **insuficiente para aprobación científica**. Presupuestos: archivo 16 MiB, 2000 muestras, 50 000 caracteres por muestra y dos millones combinados.

## Baseline, calibración y trazabilidad

Regresión logística L2 de ocho características observables, estandarización ajustada solo en train, inicialización cero y descenso por lotes con parámetros fijos. Calibración de Platt ajustada solo en calibration. Validation/test no alteran escalas, coeficientes ni calibración. Implementación pequeña con biblioteca estándar de Python, sin scikit-learn, PyTorch, GPU ni dependencias nuevas.

Métricas binaria a umbral técnico 0,5: matriz de confusión, precision, recall, F1, FPR con intervalo Wilson 95 %, Brier y ECE en diez bins. Desgloses por idioma, dominio y generador; denominadores vacíos producen null/no evaluado. Las métricas del conjunto calibration son de ajuste, no evaluación independiente. No se seleccionan umbrales, hiperparámetros o aprobaciones con test. No hay búsqueda de hiperparámetros. Los informes no ocultan el tamaño de muestra y no contienen textos originales.

El experimento produce model.json (números, no pickle/código ejecutable), report.json, manifest.json y execution.json en un directorio privado e inmutable identificado por hash. Identidad: corpus y permisos declarados, versión/características, algoritmo, hashes de parámetros/informe/código. La ejecución registra Python/plataforma y tiempo real. Mismos datos y código producen la misma identidad; no se sobreescriben experimentos existentes. Todos permanecen sin aprobar. Los hashes de model/report se calculan sobre JSON canónico sin el salto de línea final.

## API, privacidad y verificación

GET `/api/v1/experimental-ai/capabilities` declara observaciones disponibles y clasificador/entrenamiento web no disponibles. GET `/api/v1/experimental-ai/documents/{id}` revalida sesión, institución y permisos documentales, requiere extracción completada/parcial y responde con estadísticas originales, procedencia y abstención. Cálculo bajo bloqueo documental, 300 lecturas por miembro/quince minutos, 413 ante presupuesto excedido y 409 si extracción no está lista. No persiste resultados derivados ni cambia el esquema `0007_claims`: borrar/revocar acceso impide nuevas lecturas. La pantalla oculta resultados ante errores de acceso y refresca permisos periódicamente.

[Protocolo y comandos](../evaluation/experimental-ai-v1/README.md). [Validación observada](validation/phase8/README.md). Los límites previos de OCR, contención del parser, proveedores externos, semántica, Windows y producción continúan. No se presentan métricas sintéticas como exactitud científica ni se reutilizan documentos privados para entrenamiento.
