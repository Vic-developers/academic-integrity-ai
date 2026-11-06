# Academic Integrity AI

## Fase 7 — Afirmaciones y evaluación humana

La fase 7 local permite proponer afirmaciones, recuperar pasajes de fuentes seleccionadas y registrar decisiones humanas con evidencia e historial. No se habilitó Hugging Face. NLI, artículos externos y clasificación automática permanecen pendientes; no se inicia fase 8. [Alcance detallado](docs/PHASE_7.md).

## Fase 6 — Bibliografía local y adaptadores de metadatos

Bibliografía permite extraer referencias candidatas, DOI, posibles duplicados y patrones de citas; conserva texto, rangos y hashes y exporta evidencia JSON. Crossref/OpenAlex tienen adaptadores y estados de cobertura, pero sus consultas reales fueron rechazadas por la red de esta sesión. No se presenta ninguna fuente como verificada externamente sin una respuesta válida.

[Alcance implementado y límites](docs/PHASE_6.md), [contrato API](docs/BIBLIOGRAPHY_API.md). La validación real en línea permanece pendiente; el modo local funciona sin esos proveedores. Hugging Face y la inferencia semántica siguen pospuestos según la decisión previa.

## Continuación sin Hugging Face — Infraestructura vectorial

Por decisión del usuario se continúa sin habilitar Hugging Face ni descargar modelos. Se añadió la infraestructura interna de pgvector: vectores privados por institución/versión/fragmento, búsqueda exacta filtrada, caché inmutable y borrado de derivados. No se generan embeddings ni hallazgos semánticos; la comparación literal y el visor PDF siguen disponibles.

[Alcance y límites](docs/PHASE_5_VECTOR.md). La parte de la fase 5 que requiere modelo y evaluación semántica queda pospuesta, sin pedir cambios de red.

## Fase 5 en preparación

La corrección PDF y la fase 4 están publicadas en GitHub hasta `0a8db5e`. La fase 5 fue autorizada y continúa sin habilitar Hugging Face, por decisión del usuario. Hay instalador y controles preparados, pero no se ha descargado ni evaluado un modelo y la similitud semántica continúa no disponible. [Trabajo y bloqueo](docs/PHASE_5_PREPARATION.md).

## Corrección posterior del PDF

El visor aplica la transformación real de PDF.js a las cajas originales y admite las cuatro rotaciones, CropBox, orígenes desplazados y UserUnit. Conserva compatibilidad con versiones ya extraídas; solo omite el overlay cuando la referencia o los caracteres no son verificables. [Verificación](docs/validation/pdf-correction/README.md).

## Estado actual — Fase 4

Visor comparativo de evidencias con resaltado de rangos originales, contexto, navegación, solapamientos, filtros, revisión humana con historial y exportación JSON. PDF con cajas de caracteres cuando la geometría es verificable; DOCX/TXT estructurados. [Fase 4 y límites](docs/PHASE_4.md), [verificación](docs/validation/phase4/README.md).

Push previo confirmado en GitHub (rama work, 30e05a4). La fase 5 está autorizada y en preparación, pendiente de verificar el modelo. Web permanece no disponible; las coincidencias no determinan plagio.

La base incluye autenticación institucional, carga privada PDF/DOCX/TXT y extracción asíncrona. La comparación literal consulta solo las fuentes autorizadas seleccionadas. OCR no está integrado; las páginas sin texto muestran cobertura parcial.

Contratos: [API documental](docs/DOCUMENT_API.md), [API literal y revisión](docs/LITERAL_API.md). La [evaluación técnica sintética](evaluation/literal-v1/README.md) no acredita validez académica general. Verificaciones realizadas en Linux CPU, sin GPU ni APIs comerciales de análisis.

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
- [Fase 0](docs/PHASE_0.md), [revisión de entorno](docs/REVIEW_2026-11-05.md), [Fase 1](docs/PHASE_1.md), [Fase 2](docs/PHASE_2.md), [Fase 3](docs/PHASE_3.md), [Fase 4](docs/PHASE_4.md), [cambios](CHANGELOG.md).

Las versiones de investigación de Fase 0 son históricas. Los locks actuales y manifiestos de validación identifican las versiones efectivamente instaladas. La Fase 4 está implementada; la infraestructura vectorial de Fase 5 avanza y su parte de modelo queda pospuesta. Se publicó con autorización el trabajo previo hasta 30e05a4 en la rama work. La fase 4 se conserva inicialmente en Git local; no se ha desplegado un servicio público.

## Uso documental

Tras iniciar sesión, crea una asignatura y actividad si corresponde, matricula estudiantes autorizados y carga archivos en Documentos. Puedes cargar sin actividad para trabajo propio. El procesamiento ocurre en segundo plano; abre el documento para revisar original, texto extraído y limitaciones. Los primeros parsers admiten Linux x86_64/aarch64; el backend nativo Windows no está validado: utilizar Docker/WSL2.

## Comparación literal

En Comparaciones selecciona un documento principal y las fuentes autorizadas que deseas consultar. Espera la extracción, inicia el trabajo y revisa citas, rangos, versiones y cobertura en el resultado. También puedes abrirlo desde el documento. Una búsqueda web solicitada queda parcial porque actualmente no existe proveedor conectado.
