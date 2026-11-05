# Fase 2 — Gestión documental

Fecha: 5 de noviembre de 2026. Alcance: carga y extracción documental reales; no se inicia Fase 3.

## Funcionalidad entregada

- Carga individual, múltiple y por arrastrar/soltar de PDF, DOCX y TXT UTF-8. Un lote puede aceptar unos archivos y devolver errores específicos para otros.
- Límites de archivo/lote/cantidad, comprobación de firma/contenido, validación estructural DOCX y detección de corrupción/cifrado durante el procesamiento asíncrono.
- Originales privados inmutables para las rutas del producto, permisos 0400, claves generadas por UUID y SHA-256 comprobado antes de extraer. Descargas autorizadas como adjunto, sin caché pública.
- Duplicados identificados exclusivamente entre documentos que el usuario ya puede ver; no se revela la existencia de archivos de otra institución o de otro estudiante.
- Asignaturas, actividades, matrículas y carga en nombre de un estudiante autorizado. Docentes consultan entregas de sus actividades; estudiantes sus documentos; administración/auditoría según rol institucional.
- Cola de extracción en PostgreSQL; Celery/Redis son el mecanismo de activación. Leases, token de ejecución, recuperación de interrupciones, intentos acotados y descarte de resultados cancelados/obsoletos.
- Extracción PDF con pdfplumber/pdfminer, DOCX con python-docx y TXT local. Cada fragmento conserva original, normalizado, rangos por puntos de código Unicode, oraciones, contexto y localizadores originales.
- PDF conserva cajas de palabras/caracteres, marco, dimensiones y rotación; DOCX conserva parte OOXML, bloques, tablas y runs cuando el mapeo es fiable. No se inventa paginación Word.
- Visor PDF.js local con páginas y zoom; vistas estructuradas DOCX/TXT, texto normalizado opcional, metadatos contextuales, descarga y estados reales.
- Cancelación y eliminación lógica inmediata; trabajo durable para retirar original y fragmentos. No se afirma eliminación de backups o de todo registro administrativo: eso requiere la política de retención institucional.

## Estados y alcance

`received`, `extracting`, `completed`, `partial`, `failed`, `cancelled` son estados de extracción. Completado no significa auditoría aprobada ni originalidad verificada. PDF sin texto: `partial`, página identificada y OCR no disponible. OCR no está instalado/integrado en el worker de esta entrega; no se simula ni se descartan silenciosamente páginas.

PDF se segmenta por líneas; el orden de lectura de columnas y los párrafos semánticos requieren revisión. El texto PDF es una representación extraída: sus offsets no son offsets de bytes del PDF. TXT interpreta form feed como separación de página; DOCX muestra estructura, no diseño exacto de Word. La segmentación de oraciones es heurística. Los resaltados de coincidencias y la calibración de ubicación completa pertenecen a Fase 4.

## Seguridad comprobada y límites

RLS forzada y FK compuestas en las siete tablas nuevas, además de autorización de propietario/asignatura en servidor. Un documento ajeno devuelve 404, también al descargar original o fragmentos. Los nombres nunca forman rutas de almacenamiento. La transacción revierte archivos nuevos si falla el commit. Datos de documentos y metadatos se muestran como texto escapado.

El parser se ejecuta en un subproceso Linux sin credenciales heredadas, con CPU/memoria/tiempo/tamaño de salida limitados. Seccomp bloquea red, creación de procesos, exec, io_uring y ABI x32; si no puede aplicar esos controles, falla explícitamente. Esto no es una VM ni una garantía contra RCE: el kernel del entorno no ofrece Landlock (ENOSYS), por lo que no se añadió contención Landlock. Antes de manejar archivos institucionales sensibles en producción, completar el aislamiento del filesystem por trabajo/tenant, el escaneo de malware y la revisión de imágenes en Fases 15–16. Actualmente no hay ClamAV ni afirmación de escaneo antivirus.

Los enlaces externos de DOCX no se siguen; se rechazan relaciones externas distintas de hipervínculos y XML peligroso. El original PDF se visualiza después de terminar su extracción. No se ejecutan instrucciones de documentos ni se invocan agentes/modelos a partir de ellas.

## Dependencias y correcciones verificadas

PDF.js 5.7.284 fue descartado tras el aviso alto GHSA-hq66-cqwq-w95j. Se actualizó a 6.5.438 y se repitieron auditoría/build/pruebas. Nginx sirve el worker .mjs como JavaScript y la navegación móvil permite varias líneas. Los parsers y dependencias están bloqueados con hashes; fuentes/licencias y auditorías en [validation/phase2](validation/phase2/README.md).

PyMuPDF no se incorporó. pdfplumber es MIT, confirmado también en LICENSE de su wheel; python-docx MIT y multipart Apache-2.0. PDFium y componentes nativos conservan obligaciones/notices de sus dependencias. Metadatos de licencias no sustituyen revisión de distribución comercial.

## Validación real

Resultado final: **45 pruebas de backend y 4 recorridos de navegador aprobados**.

Consultar [checks](validation/phase2/checks.json): pruebas backend con PostgreSQL/Redis/SMTP reales y parsers en subprocesos, pruebas de navegador con Celery y archivos válidos, builds, migraciones y auditorías. Las fixtures son sintéticas y explícitas, usadas únicamente en aid_test/Redis DB 15 y un subdirectorio de almacenamiento de pruebas. No existen análisis académicos inventados ni cuentas predeterminadas en desarrollo.

El entorno tiene 2 CPU/8 GiB y disco raíz de aproximadamente 8 GiB. El driver Docker vfs agotó el disco al duplicar capas. Para las comprobaciones de contenedores se compactó localmente el filesystem de PostgreSQL/pgvector, manteniendo su volumen de datos y configuración esencial; la referencia oficial fijada por digest del proyecto permanece intacta. No se promete que una instalación completa quepa en 8 GiB: reservar al menos 30 GiB libres. Las imágenes finales API/frontend se construyen desde los Dockerfiles del repositorio.

Windows/WSL2 y CI remoto no se ejecutaron; SMTP de producción, OCR, antivirus y despliegue público siguen pendientes. Ningún motor de coincidencias, IA o búsqueda web está implementado todavía. No se ha hecho push. Para continuar se requiere autorización de Fase 3.
