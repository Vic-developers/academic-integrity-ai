# Validación — Fase 6

Linux CPU, sin nuevas dependencias ni modelos. [Comprobaciones](checks.json), [pruebas reales de acceso a proveedores](provider-probe.json). Las dos conexiones al origen fallaron; no hay metadatos reales verificados en línea en esta sesión.

Backend: scripts/test_backend.py con aid_test/Redis 15. Proveedores: fixtures de contrato explícitamente técnicos, sin solicitudes remotas en esas pruebas. Navegador: scripts/run_e2e.py con worker real y un documento bibliográfico sintético. Se prueba extracción, duplicados, cobertura externa cero, persistencia, exportación y vista móvil, junto con las regresiones previas.

Se comprueban migraciones, código/activos contra contenedores, datos de desarrollo y limpieza de archivos. La preparación iteró la nueva migración solo en aid_test antes de publicarla; no cambió migraciones históricas ni datos de desarrollo para ajustar el esquema de prueba.

El escaneo de dependencias previo se conserva como referencia histórica: los locks no cambiaron y no se afirma una nueva auditoría integral. Ni la corrección de patrones ni el contrato de un proveedor sustituyen una validación académica representativa o pruebas reales de integración remota.

La suite de navegador aísla sus contadores de login entre casos mediante un script local restringido a Redis 15 y aid_test. Solo limpia limit:login:ip/account; no cambia el límite de producción ni borra otros datos/colas. Sus guardas y el alcance de limpieza se prueban contra Redis de test real.

Resultado final: 134 pruebas de backend y 10 de navegador pasadas; 50 archivos backend y 205 activos frontend idénticos a contenedores. Esquema 0006_bibliography, RLS y limpieza comprobados. Cero consultas reales exitosas a proveedores; semántica permanece pospuesta.
