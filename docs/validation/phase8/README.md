# Validación de fase 8 experimental

`checks.json` registra resultados observados, procedencia de código/activos, limpieza y limitaciones. `technical-fixture-experiment/` conserva el entrenamiento real de 48 patrones inventados y **no** una validación científica de autoría. model.json es un artefacto técnico sin aprobar, ajeno al runtime; no habilita inferencia en documentos. Los informes declaran purpose technical_fixture y approved false.

`training-resources.json` registra tiempo de pared, CPU y memoria RSS medidos para esa ejecución pequeña en Linux, sin GPU. No son una estimación de rendimiento sobre corpus académicos. Los hashes model/report del manifiesto excluyen el salto de línea final; el identificador del experimento incluye corpus, código, artefactos y política no aprobada.

Las pruebas verifican conteos Unicode, decimales, MATTR contra cálculo independiente, repetición, límites, autorización del corpus, separación por grupos, duplicados y plantillas compartidas, aprendizaje de un problema numérico conocido, entrenamiento reproducible, independencia de test, calibración/métricas/denominadores e inmutabilidad de artefactos privados. La integración usa PostgreSQL/Redis reales para permisos documentales, estudiantes, otro tenant y borrado. El navegador calcula valores sobre un TXT real y verifica ausencia de probabilidad/entrenamiento, procedencia, persistencia visual, móvil y revocación por borrado.

Resultado observado: **174 pruebas backend y 12 de navegador aprobadas**. Coinciden por SHA-256 los 61 archivos Python de aplicación y los 206 activos frontend con lo servido. Esquema sin cambios (`0007_claims`), RLS documental forzada y cero datos/originales en desarrollo tras la limpieza.

Pruebas reproducibles con configuración local aislada:

```bash
python scripts/test_backend.py --tb=short
cd frontend
npm run build
cd ..
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium python scripts/run_e2e.py
```

No hay datos institucionales entrenados, corpus representativo aprobado, modelo activado, consulta a Hugging Face ni evaluación científica completada. Archivos de dependencias bloqueadas sin cambios respecto de fase 7; las auditorías de dependencias anteriores son históricas. La fase 9 no se ha iniciado. [Límites detallados](../../PHASE_8.md).
