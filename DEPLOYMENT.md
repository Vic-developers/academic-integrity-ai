# Infraestructura y operación

## Estado actual — Fase 4

Revisión Alembic esperada: 0004_review. API y worker deben ejecutar la misma imagen. Sin nuevas dependencias ni GPU. La exportación JSON usa sesión y permisos de auditoría; no se crea enlace público de descarga.

## Antecedente — Fase 3

Migración esperada actual: 0003_literal. API y worker deben usar la misma imagen/código. El worker procesa extracción y auditorías durables; no necesita GPU ni proveedor comercial. Los límites predeterminados son para desarrollo, sin benchmark de producción. No se ha desplegado públicamente.


## Antecedente histórico — Fase 2

Compose incorpora un volumen privado documents, compartido por API/worker con UID 10001. PDF.js y sus recursos se sirven localmente, sin CDN. Reconstruir imágenes y migrar antes de arrancar Fase 2; ver [DEVELOPMENT](docs/DEVELOPMENT.md). Mantener el volumen database y documents al actualizar.

## Antecedente histórico — cierre de Fase 1

Fase 1 incorpora Compose local y comandos de instalación reales en [README](README.md) y [DEVELOPMENT](docs/DEVELOPMENT.md). Las imágenes y dependencias se construyeron/probaron en Linux CPU. No es configuración de producción ni instalación Windows comprobada. La inspección del 3 de noviembre de abajo se conserva como histórica.

## Inspección real

3 de noviembre de 2026: checkout vacío, rama local work sin commits al inicio; Python 3.12.14, Node 24.19.0, npm 11.9.0 y cliente Docker 28.4.0. Se observaron 5 CPU, 33 GiB de memoria visible y unos 60 GiB libres en filesystem. Los límites cgroup consultados son 32 GiB de memoria y cuota equivalente a 4 CPU (cpu.max 400000/100000); dimensionar workers con esta cuota, no con los 5 procesadores visibles. No son una garantía de capacidad de aplicación. No se ha probado el daemon Docker ni construido imágenes. Proxy HTTP de plataforma obligatorio, TLS conservado; no VPN configurada. Se inspeccionaron solo nombres/presencia de variables, nunca valores.

## Servicios previstos

Compose desarrollo: frontend Vite, API, worker, despachador/outbox, PostgreSQL 16 con pgvector, Redis, volumen privado; OCR y buzón de desarrollo opcionales. Producción: reverse proxy TLS, frontend compilado, API/worker no root, DB y Redis no expuestos a Internet, objetos privados, métricas y backups. Imágenes fijadas por digest y escaneadas en Fase 1/16. Revisar guía Docker del entorno antes de construir: proxy y CA deben propagarse sin incrustar secretos.

Workers reinician después de restaurar snapshot del entorno; no suponer que sobreviven procesos. Migraciones como tarea explícita antes de servir tráfico. Readiness comprueba esquema y dependencias; liveness no consulta terceros. Prueba funcional usa login/carga/comparación y no solo puerto abierto.

## Hardware: presupuestos iniciales, no benchmarks

| Perfil | CPU/RAM/disco propuestos | Uso |
|---|---|---|
| Desarrollo sin modelos | 4 vCPU, 8 GiB, 30 GiB SSD | API, UI, BD y comparación literal |
| Desarrollo semántico/OCR | 8 vCPU, 16–32 GiB, 80 GiB | Embeddings CPU por lotes, OCR limitado |
| Piloto institucional | 8 vCPU, 32 GiB, almacenamiento separado | Validar con carga real antes de contratar SLA |
| Entrenamiento | GPU opcional 12–24 GiB VRAM, RAM 32+ GiB | Según modelo/dataset; no requerido por funciones esenciales |

OCR y modelos usan colas con concurrencia limitada a 1 inicialmente, ajustada tras medir. No descargar LLM grandes por defecto. Confirmar soporte de wheels y arquitectura de CPU. Extraer grandes lotes bajo límites de memoria; GPU no garantiza calidad.

## Configuración futura

DATABASE_URL, broker URL y credenciales de objetos como secretos del despliegue; no agregar valores a Git. Configuración no secreta: límites, retención, orígenes CORS, proveedores activados y rutas privadas. El almacenamiento no usa carpetas públicas. Generar claves de sesión/webhook en sistema de secretos. Correo de recuperación requiere SMTP o proveedor autorizado en producción. Ningún secreto nuevo es necesario para Fase 0.

Dominios potenciales: registros PyPI/npm e imágenes, repositorios de modelos aprobados, api.crossref.org, api.openalex.org y dominios concretos de fuentes aprobadas. No solicitar wildcard de Internet por defecto; preservar allowlist existente. Acceso a registries probado para investigación, no prueba de acceso a todos los proveedores. Las credenciales de Moodle se aportarán en configuración segura al iniciar su integración.

## Costes y límites externos

Licencias permisivas reducen coste de software, no eliminan CPU, almacenamiento, backups, transferencia, correo, observabilidad ni mantenimiento. PyMuPDF comercial requiere presupuesto si se escoge; no se ha solicitado cotización. Búsqueda web puede tener cuotas/precio y no se garantiza proveedor general gratuito. APIs académicas pueden requerir cuenta/clave y cambiar condiciones. Moodle exige instancia de prueba y administración autorizada. Coste mensual = cómputo API/workers + DB + GB de originales/snapshots/informes + backups + egress + correo + proveedor de búsqueda; no hay tarifas verificadas ni importe mensual presupuestado.

## Resiliencia y publicación

Copias cifradas, DB con PITR cuando lo permita el operador, objetos versionados y prueba de restauración. Objetivos iniciales propuestos RPO ≤24 h y RTO ≤4 h, pendientes de ensayo y contrato. Registrar longitud de cola, jobs huérfanos, latencia, errores de proveedor y uso de cuotas sin texto académico. Manual de incidentes y responsables antes de producción.

Windows: prever WSL2 + Docker Desktop, checkout en filesystem Linux y puertos restringidos; PowerShell solo para invocar herramientas documentadas cuando existan. No se ha ejecutado instalación Windows. No hay comandos docker compose que funcionen aún: se crearán y probarán en Fase 1. No se modificó el borrador del entorno ni se publicó nada durante Fase 0.

## Revisión actual

La inspección del 5 de noviembre de 2026 y sus límites están en [REVIEW_2026-11-05](docs/REVIEW_2026-11-05.md). Los recursos históricos no describen la sesión actual.
