# Academic Integrity AI

## Estado real — Fase 3

Comparación literal asíncrona con fuentes institucionales elegidas explícitamente, rangos y citas verificables, versiones/SHA-256, cobertura y permisos reales. No hay proveedor web configurado: cero búsquedas y fuentes web verificadas. La cobertura describe texto extraído y fuentes seleccionadas; no determina plagio.

Ver [Fase 3](docs/PHASE_3.md), [API literal](docs/LITERAL_API.md) y [evaluación técnica](evaluation/literal-v1/README.md). El visor de resaltado exacto de fase 4 sigue pendiente de autorización.


Plataforma de apoyo a la revisión académica con evidencias verificables y decisión humana.

## Antecedente — Fase 2

Carga privada PDF/DOCX/TXT, extracción asíncrona real, hash, duplicados visibles, asignaturas/actividades/matrículas y vistas PDF/estructuradas implementados, junto con la autenticación y roles de Fase 1.

Un estado de extracción completada no implica originalidad ni auditoría académica. OCR no está integrado: páginas PDF sin texto muestran resultado parcial. En ese cierre aún no existían comparaciones; modelos, informes y Moodle siguen pendientes.

Resultados y límites: [Fase 2](docs/PHASE_2.md), [API documental](docs/DOCUMENT_API.md). Las comprobaciones se ejecutaron en Linux CPU, sin GPU ni APIs comerciales de análisis.

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
- [Fase 0](docs/PHASE_0.md), [revisión de entorno](docs/REVIEW_2026-11-05.md), [Fase 1](docs/PHASE_1.md), [Fase 2](docs/PHASE_2.md), [cambios](CHANGELOG.md).

Las versiones de investigación de Fase 0 son históricas. Los locks actuales y manifiestos de validación identifican las versiones efectivamente instaladas. La Fase 3 está implementada; la Fase 4 requiere autorización expresa. No se ha hecho push ni desplegado un servicio público.

## Uso documental

Tras iniciar sesión, crea una asignatura y actividad si corresponde, matricula estudiantes autorizados y carga archivos en Documentos. Puedes cargar sin actividad para trabajo propio. El procesamiento ocurre en segundo plano; abre el documento para revisar original, texto extraído y limitaciones. Los primeros parsers admiten Linux x86_64/aarch64; el backend nativo Windows no está validado: utilizar Docker/WSL2.

## Comparación literal

En Comparaciones selecciona un documento principal y las fuentes autorizadas que deseas consultar. Espera la extracción, inicia el trabajo y revisa citas, rangos, versiones y cobertura en el resultado. También puedes abrirlo desde el documento. Una búsqueda web solicitada queda parcial porque actualmente no existe proveedor conectado.
