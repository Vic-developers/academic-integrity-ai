# Academic Integrity AI

Plataforma de apoyo a la revisión académica con evidencias verificables y decisión humana.

## Estado real

Fase 0 — investigación y arquitectura, 3 de noviembre de 2026. Este repositorio contiene diseño y documentación, no una aplicación ejecutable. No existen todavía motores, modelos entrenados, API, usuarios, migraciones ni pruebas funcionales. No hay resultados de análisis ni métricas científicas. No se ha desplegado ni publicado el proyecto.

La siguiente fase requiere autorización expresa. La publicación del entorno es distinta de un push de Git y del despliegue del producto.

## Documentación

- [Arquitectura y estructura](ARCHITECTURE.md).
- [Requisitos y aceptación](REQUIREMENTS.md).
- [Datos y aislamiento](DATABASE.md).
- [Contratos REST y motores](API.md).
- [Seguridad y privacidad](SECURITY.md).
- [Modelos y abstención](AI_MODELS.md).
- [Evaluación y pruebas](EVALUATION.md).
- [Infraestructura, hardware y costes](DEPLOYMENT.md).
- [Integración Moodle](MOODLE_INTEGRATION.md).
- [Fases y riesgos](ROADMAP.md).
- [Interfaces y posiciones](docs/UX.md).
- [Decisiones y alternativas](docs/DECISIONS.md).
- [Investigación y validación tecnológica](docs/RESEARCH.md).
- [Registro de cambios](CHANGELOG.md).

## Desarrollo futuro

Se utilizará el checkout existente: cada tarea de nube ya está aislada; no crear worktrees sin petición expresa. La Fase 1 aportará comandos de instalación reproducibles, lockfiles, Compose, migraciones y pruebas. No se ofrecen comandos de arranque ficticios en esta fase. Windows utilizará WSL2 y Docker Desktop con integración de WSL, sujeto a validación durante esa fase. No hacen falta credenciales comerciales para diseñar ni para la comparación institucional prevista.
