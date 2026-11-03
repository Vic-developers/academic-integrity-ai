# Investigación y validación tecnológica

Fecha de consulta: 2026-11-03. Se consultaron por HTTPS con verificación TLS los registros oficiales PyPI/npm y código oficial de Moodle. Las copias se conservan para trazabilidad; no son dependencias instaladas. No se creó aplicación ni se alteró la configuración publicada del entorno.

## Niveles de validación

1. **Verificado:** herramientas presentes, existencia de las versiones consultadas, metadatos declarados de licencia/runtime y existencia de APIs en el tag Moodle.
2. **Compatibilidad declarada:** requisitos Python de estos paquetes permiten Python 3.12; Vite 6, React Router 7 y PDF.js 5 declaran rangos Node que admiten Node 24. No equivale a resolver todas las dependencias ni probarlas.
3. **Pendiente de Fase 1:** resolución conjunta con lockfiles, compilación, pruebas reales, escaneo de vulnerabilidades, SBOM y licencias transitivas. Para modelos, evaluación y licencia exacta del artefacto en Fase 5/8. No se presenta el stack como integrado o apto para producción.

## Versiones de referencia consultadas

Las siguientes versiones son referencias concretas para comprobar interfaces y requisitos, no una selección de versiones mantenidas para producción en noviembre de 2026. Antes de bloquear dependencias, consultar releases mantenidos, avisos y resolver versiones compatibles. Nunca instalar ciegamente estas referencias antiguas. La arquitectura elige familias tecnológicas; el lock reproducible se aprueba en Fase 1.

| Paquete | Versión consultada | Licencia declarada o identificada |
|---|---|---|
| fastapi | 0.115.12 | MIT (LICENSE oficial consultado) |
| pydantic | 2.11.4 | MIT |
| SQLAlchemy | 2.0.40 | MIT |
| alembic | 1.15.2 | MIT |
| psycopg | 3.2.9 | LGPL-3.0; revisar distribución y obligaciones |
| celery | 5.5.2 | BSD-3-Clause |
| pymupdf | 1.25.5 | Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License |
| python-docx | 1.1.2 | MIT |
| sentence-transformers | 4.1.0 | Apache 2.0 |
| transformers | 4.51.3 | Apache 2.0 License |
| torch | 2.7.0 | BSD-3-Clause |
| scikit-learn | 1.6.1 | BSD-3-Clause |
| react | 19.1.0 | MIT |
| typescript | 5.8.3 | Apache-2.0 |
| vite | 6.3.5 | MIT |
| tailwindcss | 4.1.5 | MIT |
| @tanstack/react-query | 5.76.0 | MIT |
| react-router | 7.6.0 | MIT |
| react-hook-form | 7.56.3 | MIT |
| zod | 3.24.4 | MIT |
| pdfjs-dist | 5.2.133 | Apache-2.0 |
| recharts | 2.15.3 | MIT |

## Selección PDF y obligaciones

PyMuPDF declara AGPL/comercial: no incorporarlo automáticamente a un SaaS propietario. pdfplumber 0.11.10 requiere Python >=3.8 y declara pdfminer.six==20260107, Pillow>=12.2.0 y pypdfium2>=5.9.0. Su metadato de licencia consultado está vacío: verificar LICENSE de la distribución exacta y dependencias antes de aprobarlo. pypdfium2 5.14.0 declara BSD-3-Clause, Apache-2.0 y licencias de dependencias. PDFium exige conservar notices; no inferir que todos los binarios tienen una única licencia. La alternativa elegida es evaluación de extracción permisiva y PDF.js para visualización, condicionada a esa revisión. Tesseract (candidato Apache-2.0), PostgreSQL (PostgreSQL License) y pgvector (PostgreSQL License) aún requieren comprobar artefactos concretos. Redis cambia condiciones por versión: seleccionar release/licencia explícita en Fase 1 y revisar impacto del despliegue; no asumir licencia BSD para cualquier versión.

## Fuentes y reproducibilidad

- [Metadatos de dependencias](research/dependencies.json): URL exacta, versión, requisitos y estado de consulta.
- [Fuentes oficiales adicionales](research/sources.json): URLs Moodle y alternativas PDF.
- Moodle: las copias conservan cabeceras de licencia; solo material de investigación, no plugin implementado.
- Consultar política comercial y límites vigentes de Crossref/OpenAlex antes de activar conectores; no se probaron APIs bibliográficas ni buscador general.
- No hay comprobaciones de Windows, daemon Docker, PostgreSQL, GPU o inferencia en esta fase.

## Puertas de aprobación tecnológica

Fase 1 debe resolver y bloquear frontend/backend, revisar avisos de seguridad y licencias transitivas, construir imágenes y ejecutar autenticación/aislamiento con BD real. Fase 2 debe demostrar extracción con geometría; una alternativa PDF que no lo logre debe revisarse. Fase 5 debe fijar revisión/licencia de embeddings y medir español. Fase 8 debe aportar datos autorizados y calibración o conservar abstención. Estas puertas no se sustituyen por una consulta exitosa a un registro.
