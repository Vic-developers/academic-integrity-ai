# Validación de Fase 3

Ejecución local Linux CPU, 2026-11-05. Artefactos: [corpus y métricas](literal-evaluation.json), [licencias runtime](runtime-licenses.json), [auditoría Python](python-audit.json), [auditoría frontend](frontend-audit.json). [Comprobaciones de cierre](checks.json): 65 pruebas backend y 5 de navegador pasadas, imágenes compiladas, 35 archivos de aplicación idénticos entre checkout y contenedor, revisión 0003_literal y cero usuarios/documentos/cursos/auditorías en la base de desarrollo tras las pruebas. Cero originales de prueba restantes y cero vulnerabilidades conocidas reportadas en ambos escáneres de dependencias.

Backend: `python scripts/test_backend.py --tb=short`, base aislada aid_test, Redis 15. Navegador: `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium python scripts/run_e2e.py`, stack y worker reales, documentos sintéticos. El script limpia únicamente su almacenamiento de prueba y restaura el entorno de desarrollo.

No se ha comprobado Windows, despliegue público ni un proveedor web. Los escáneres de dependencias no equivalen a una auditoría integral de seguridad. La evaluación sintética no acredita exactitud académica general.
