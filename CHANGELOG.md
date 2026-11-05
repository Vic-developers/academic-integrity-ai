# Registro de cambios

## Fase 0 — 2026-11-03

- Inspeccionado entorno y repositorio inicialmente vacío.
- Definida arquitectura modular, datos, contratos, motores y visualizador.
- Documentados seguridad, evaluación, operación, costes, riesgos y puertas por fase.
- Consultados metadatos públicos de dependencias y fuentes de Moodle 5.0.2.
- Sin aplicación implementada, modelos evaluados, despliegue, push ni publicación.

## 2026-11-05 — Revisión de Fase 0

Revisados documentos, enlaces y hashes locales; registrada capacidad actual (2 CPU/8 GiB), CPU como objetivo y fallo de acceso remoto. Se conserva arquitectura previa y la separación entre diseño y validación ejecutable. Sin implementación de Fase 1 ni publicación.

## 2026-11-05 — Fase 1

Implementados infraestructura, migración, sesiones, recuperación SMTP con cola durable, seis roles, RLS, alta por CLI, interfaz institucional y pruebas reales. Locks con hashes, bases Docker fijadas por digest, auditorías de dependencias y CI preparado. Sin carga documental ni motores. Resultados y límites en [PHASE_1](docs/PHASE_1.md).

## 2026-11-05 — Fase 2

Gestión documental real PDF/DOCX/TXT, originales privados, cola durable con leases, mapas Unicode y coordenadas PDF, DOCX estructurado, asignaturas/actividades/matrículas y visualizador. Cancelación, purga y rollback de archivos. PDF.js actualizado a 6.5.438 por aviso de seguridad. OCR no disponible declarado; sin motores de comparación ni publicación. Ver [Fase 2](docs/PHASE_2.md).
