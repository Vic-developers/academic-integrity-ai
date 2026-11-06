# Validación de fase 7 local

`checks.json` registra resultados observados, esquema, RLS, hashes de código/activos servidos y limpieza de datos de prueba. Entorno Linux con CPU; PostgreSQL real con pgvector, Redis y Celery. No se realizaron consultas externas ni inferencia NLI.

Resultado observado: **154 pruebas backend y 11 de navegador pasaron**. Los 56 archivos Python de aplicación y los 205 activos frontend coinciden por SHA-256 con los contenedores servidos. Esquema `0007_claims`, cuatro tablas con RLS forzada y cero datos/originales en desarrollo tras la limpieza.

Comandos reproducibles en el entorno de desarrollo configurado:

```bash
python scripts/test_backend.py --tb=short
cd frontend
npm run build
cd ..
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium python scripts/run_e2e.py
```

Los scripts rechazan bases no locales y aislan pruebas en `aid_test` y Redis 15. El recorrido del navegador utiliza archivos TXT sintéticos, el trabajador real, exportación con pasajes originales, un conflicto concurrente y selección manual Unicode. Conserva las regresiones de autenticación, documentos, PDF y bibliografía. Al terminar, restaura servicios de desarrollo y limpia solo originales del almacenamiento de pruebas.

Las pruebas específicas comprueban extracción/negación sin clasificación automática, ausencia de fuentes, presupuestos y contexto bibliográfico omitido explícitamente, hashes/rangos, rechazo de evidencia alterada, roles e instituciones, idempotencia, cancelación durante cálculo, pérdida de permisos, agotamiento de leases y borrado de fuentes. No acreditan precisión científica, verificación de artículos externos ni inferencia semántica.

No hay dependencias nuevas: los tres archivos de versiones bloqueadas coinciden con el commit de fase 6. Las auditorías de dependencias de fases anteriores son históricas; no se presentan como nuevos escaneos. No se habilitó Hugging Face ni se modificó la política de red. Persisten los límites de [fase 7](../../PHASE_7.md).
