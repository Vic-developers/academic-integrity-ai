# Academic Integrity AI

Plataforma de apoyo a la revisión académica con evidencias verificables y decisión humana.

## Estado real — Fase 1

Infraestructura y acceso implementados: React/TypeScript, FastAPI, PostgreSQL 16 con pgvector, Redis, worker Celery y buzón SMTP local. Inicio/cierre de sesión, recuperación de contraseña, selección institucional, seis roles, usuarios y actividad con autorización del servidor. El dashboard consulta miembros reales de la base seleccionada. No contiene métricas de auditorías ficticias.

Carga documental, extracción, motores, evidencias académicas e informes aún no están implementados: comienzan en Fase 2 y siguientes. La disponibilidad local no equivale a producción ni a validación científica. Ver [resultado de Fase 1](docs/PHASE_1.md).

## Inicio en Windows / PowerShell

Requisitos: Python 3.12 para generar configuración, Git y Docker Desktop con motor Linux/WSL2 y Compose v2. CPU sin GPU; reservar al menos 8 GiB RAM y 30 GiB libres para imágenes/cachés; 16 GiB recomendados para desarrollar. Windows no se ha ejecutado en esta sesión: los comandos son la ruta prevista, pendiente de comprobar en tu equipo.

Desde `C:\Proyectos\academic-integrity-ai`:

```powershell
py -3.12 scripts/configure_dev.py
docker compose up --build -d
docker compose ps
```

El script genera contraseñas aleatorias y no sobrescribe `.env`. No existen cuentas por defecto. Crear la primera institución y su administrador con el comando interactivo:

```powershell
docker compose run --rm migrate python -m app.cli --institution "Mi institución" --email "administrador@tu-dominio.edu" --name "Administrador"
```

Se solicita la contraseña sin mostrarla. Abrir http://localhost:5173; seleccionar la institución después del login. Buzón local de recuperación: http://localhost:8025. No usar el buzón de desarrollo para correo real ni exponer estos puertos públicamente. La base de datos y Redis no publican puertos en el Compose normal.

En Linux, sustituir `py -3.12` por `python3.12`. Consultar [guía de desarrollo y pruebas](docs/DEVELOPMENT.md) para ejecutar servicios desde el host. Los secretos se leen del entorno, nunca deben subirse a Git.

## Documentación

- [Arquitectura](ARCHITECTURE.md), [datos](DATABASE.md), [requisitos](REQUIREMENTS.md), [API](API.md).
- [Seguridad](SECURITY.md), [modelos](AI_MODELS.md), [evaluación](EVALUATION.md).
- [Instalación e infraestructura](DEPLOYMENT.md), [Moodle](MOODLE_INTEGRATION.md), [hoja de ruta](ROADMAP.md).
- [UX y posiciones](docs/UX.md), [decisiones](docs/DECISIONS.md), [investigación histórica](docs/RESEARCH.md).
- [Fase 0](docs/PHASE_0.md), [revisión de entorno](docs/REVIEW_2026-11-05.md), [Fase 1](docs/PHASE_1.md), [cambios](CHANGELOG.md).

Las versiones de investigación de Fase 0 son históricas. Los locks de Fase 1 y manifiestos de validación identifican las versiones efectivamente instaladas. La Fase 2 requiere autorización expresa. No se ha hecho push ni desplegado un servicio público.
