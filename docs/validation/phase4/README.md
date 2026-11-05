# Validación de Fase 4

Linux CPU, 2026-11-05. [Comprobaciones de cierre](checks.json), [licencias](runtime-licenses.json), [Python](python-audit.json) y [frontend](frontend-audit.json).

Comandos: `python scripts/test_backend.py --tb=short`; `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium python scripts/run_e2e.py`; compilación de imágenes mediante Compose y TypeScript estricto; `ruff check backend scripts evaluation`.

Las pruebas usan aid_test/Redis 15, archivos sintéticos y worker real. Se restaura desarrollo y se comprueban hashes de código del contenedor, esquema y limpieza de originales. La prueba geométrica exige píxeles oscuros del PDF dentro de más del 85 % de cajas de caracteres de un fixture conocido y comprueba escalado de zoom; no es un benchmark sobre PDFs arbitrarios. Rotación y mapa alterado verifican abstención de resaltado.

No se han probado Windows/WSL2 ni producción. Sin OCR ni proveedor web. Los informes de dependencias no sustituyen una auditoría integral de seguridad.

El cierre incluye 74 pruebas backend y 8 de navegador, conservación del borrador ante conflicto de revisión y comparación byte a byte de activos frontend compilados localmente frente a los servidos por el contenedor. Las fuentes de Tailwind están declaradas explícitamente para evitar incluir clases de archivos generados.
