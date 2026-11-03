# Registro de decisiones

| Decisión | Alternativas consideradas | Justificación y condición de revisión |
|---|---|---|
| Monolito modular + workers | Microservicios | Menor coste operativo, transacciones claras; separar servicio solo con necesidad medida |
| PostgreSQL + pgvector | DB vectorial separada | Aislamiento/transacciones comunes; revisar escala y recall filtrado |
| Celery + Redis y outbox PG | Jobs en HTTP, Redis como registro único | Durabilidad y reintentos; Redis reemplazable sin perder auditorías |
| Sesión opaca con cookie | JWT persistido en localStorage | Revocación directa y menor exposición JS; CSRF obligatorio |
| Extracción PDF permisiva | PyMuPDF AGPL/comercial | Evaluar pdfplumber/pdfminer.six y render PDF.js/PDFium; confirmar licencias transitivas y geometría en F1–2 |
| OCR Tesseract opcional | OCR comercial esencial | Despliegue local, idiomas y calidad explícitos; evaluar recursos |
| Tika diferido | Añadir Java/Tika inicialmente | PDF/DOCX/TXT cubiertos sin servicio extra; incorporar solo con beneficio probado |
| Embeddings locales candidatos | API comercial esencial | Privacidad y sustitución; no aprobar modelo sin licencia/evaluación |
| Modelo IA con abstención | Score universal de autoría | No hay evidencia científica local para prometer autoría |
| Proveedor web opcional por institución | Scraping general no autorizado | Cobertura real y términos verificables; comparación institucional es independiente |
| Almacenamiento privado local/S3 | Archivos públicos | Privacidad, control de acceso y retención |

La arquitectura queda fijada como base de implementación de Fase 1. No es una garantía de rendimiento ni decisión irreversible. Versiones candidatas de investigación no constituyen lockfile ni aprobación de producción. Antes de elegir PyMuPDF comercial, un responsable debe aceptar su coste; no se presupone autorización.
