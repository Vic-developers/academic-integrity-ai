# Validación — Infraestructura vectorial sin modelo

Linux CPU. [Comprobaciones reales](checks.json). Comandos: `python scripts/test_backend.py --tb=short`, `ruff check backend scripts evaluation` y `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium python scripts/run_e2e.py`, con imagen backend reconstruida y esquema 0005_vector.

Las 16 pruebas nuevas utilizan PostgreSQL/pgvector reales y vectores unitarios conocidos de 384 dimensiones, exclusivamente en aid_test. La suite conserva las 85 pruebas anteriores. Son pruebas de almacenamiento, matemáticas, permisos e integridad; no miden similitud semántica ni ejecutan un modelo. La aplicación mantiene ese motor desactivado.

La primera migración de prueba detectó que aid_test no tenía la extensión vector, aunque desarrollo sí. La migración nueva instala la extensión si falta; se verificó la migración y su recorrido downgrade/upgrade en la suite. La extensión compartida se conserva al deshacer el esquema de vectores.

No hay cambios de dependencias; los escaneos/locks previos se conservan como referencia histórica, sin afirmar que se hayan repetido. No se hicieron solicitudes a Hugging Face. Los datos de desarrollo, archivos originales y vectores técnicos se comprueban tras restaurar el entorno; los volúmenes se conservan.

Resultado final: 101 pruebas de backend y 9 de navegador pasadas. El código servido coincide en 42 archivos backend y 205 activos frontend. Esquema 0005_vector, RLS habilitada/forzada y limpieza verificados. Desarrollo queda sin usuarios/documentos/auditorías/vectores ni originales de prueba. No se habilitó ni consultó el origen del modelo.
