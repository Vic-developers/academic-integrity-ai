# Protocolo técnico literal v1

Ejecutar desde la raíz con Python 3.12 y dependencias backend:

```sh
PYTHONPATH=backend python evaluation/literal-v1/evaluate.py --output docs/validation/phase3/literal-evaluation.json
```

Semilla fija 20261105, 120 positivos generados con rangos de 8–64 palabras, 80 negativos disjuntos y un positivo español Unicode. Las anotaciones se generan por posiciones conocidas, independientemente de la salida del motor. No utiliza documentos de estudiantes ni fuentes web. El JSON registra hash del corpus, versiones, TP/FP/FN por posición de palabra, precisión, recall y F1; puertas técnicas: precisión ≥0,98 y recall ≥0,95.

Resultado observado: 201 casos, 4625 posiciones verdaderas positivas, cero falsas positivas/negativas en este corpus. Este diseño controlado no representa redacción académica, citas legítimas, idiomas diversos o todas las transformaciones Unicode. No estima detección de plagio, cobertura de Internet ni capacidad de producción. Se necesitan corpus autorizados representativos y revisión humana antes de cualquier afirmación académica general.
