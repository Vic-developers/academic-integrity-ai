# Validación de fase 9

`checks.json` registra resultados observados, hashes de código/activos realmente servidos, esquema, RLS y limpieza. Las pruebas verifican comportamiento y procedencia con documentos técnicos de prueba; no entrenan un detector de autoría ni acreditan precisión científica.

Cobertura: DOCX real con hidden/blanco/fuente pequeña y propiedades de autor/software; PDF real con texto blanco/pequeño; Unicode astral, invisibles, alfabetos mezclados, ligaduras, hashes y rangos originales; fechas y límites de observaciones; autorizaciones, historial, conflicto de revisión, revocación, comparabilidad declarada, estudiante, textos cortos/duplicados, privacidad y borrado. El compilador de corpus rechaza datos sin derechos declarados, rutas externas y hashes alterados. El entrenamiento rechaza por defecto los patrones técnicos de fase 8.

El recorrido de navegador carga tres documentos del estudiante, observa ubicaciones originales y exportación, registra autorizaciones como evaluador, compara medidas descriptivas y verifica que revocar una muestra retire el resultado. Conserva regresiones de acceso, documentos, geometría PDF, literal, bibliografía, afirmaciones y observaciones lingüísticas.

Resultado observado: **190 pruebas backend y 13 de navegador aprobadas**. Los 65 archivos Python de aplicación y los 207 activos frontend coinciden por SHA-256 con los contenedores servidos. Esquema `0009_forensics`, RLS documental y de autorizaciones forzada, cero datos y originales de prueba en desarrollo tras la limpieza.

```bash
python scripts/test_backend.py --tb=short
cd frontend
npm run build
cd ..
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium python scripts/run_e2e.py
```

Bases aisladas `aid_test` y Redis 15. Al terminar se restauran servicios de desarrollo y se limpian originales del volumen de pruebas, sin borrar datos ajenos. Archivos de dependencias bloqueadas sin cambios respecto de fase 8; auditorías anteriores históricas, no escaneos nuevos.

La solicitud adicional de probabilidades de autoría no se declara completada: no existe corpus real calificado ni modelo propio científicamente evaluado/calibrado. Se registran fuentes y obstáculos reales en [corpus v1](../../../datasets/authorship-v1/README.md). No se usaron pesos de Hugging Face, patrones sintéticos como datos reales, datos privados institucionales ni la copia de licencia no verificada para entrenamiento. No se cambió la política de red. [Límites de fase 9](../../PHASE_9.md).
