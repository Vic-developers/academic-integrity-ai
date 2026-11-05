# Requisitos y aceptación

## Estado actual — Fase 4

Resaltado en texto original con mapa Unicode, dos paneles, superposiciones y navegación implementados. PDF superpuesto solo con geometría compatible; fallback explícito para rotación/recorte o caracteres sin referencia. Revisión humana trazable y exportación JSON disponibles; PDF de informes y casos siguen pendientes.

## Antecedente — Fase 3

Implementada la comparación literal sobre documentos institucionales seleccionados legibles, con evidencia y cobertura. Búsqueda web declarada no disponible por falta de proveedor autorizado; no se simula. Resaltado exacto, semántica, IA e informes permanecen futuros.


## Antecedente histórico — Fase 2

La Fase 2 implementa gestión PDF/DOCX/TXT y estructura verificable, con OCR explícitamente no disponible. Los criterios y límites reales están en [PHASE_2](docs/PHASE_2.md); las comparaciones y resaltados de coincidencias siguen pendientes de sus fases.

## Antecedente histórico — cierre de Fase 1

Los criterios de infraestructura/autenticación de Fase 1 están implementados y sus resultados se documentan en [PHASE_1](docs/PHASE_1.md). La aceptación del producto completo y las capacidades de fases posteriores permanecen pendientes.

## Alcance

Usuarios: superadministrador, administrador institucional, coordinador, docente, auditor y estudiante. El rol es una membresía institucional; no una propiedad global que otorgue acceso a todos los datos. Superadministración opera metadatos y soporte con acceso excepcional explícito, temporal y auditado a documentos. Docente gestiona sus asignaciones, auditor revisa los casos asignados, estudiante consulta sus entregas cuando la política lo permita. No hay sanciones automáticas.

| Identificador | Capacidad exigida | Aceptación verificable | Fase |
|---|---|---|---|
| R01 | Sesiones y permisos | Inicio, cierre, recuperación y revocación; pruebas negativas por rol y tenant | 1 |
| R02 | Documentos PDF/DOCX/TXT | Validación real, hash, cuarentena, límites, extracción y errores específicos | 2 |
| R03 | Coincidencias exactas | Fragmentos recuperados comparados realmente con offsets verificables | 3 |
| R04 | Evidencias visibles | Selección y resaltado exactos en origen y fuente, incluso Unicode y solapes | 4 |
| R05 | Semántica multilingüe | Evaluación separada por idioma, umbral calibrado y fuentes trazables | 5 |
| R06 | Referencias | Respuesta y metadatos reales, estados parciales, sin afirmar invención por ausencia | 6 |
| R07 | Afirmaciones | Fuente y pasaje justificativo o abstención, evaluación humana reproducible | 7 |
| R08 | Indicios de IA | Modelo evaluado o abstención explícita; sin probabilidades sin calibración | 8 |
| R09 | Forense y estilo | Procedencia, autorización y límites visibles; sin inferencia automática de autoría | 9 |
| R10 | Comparación masiva | Matriz y grafo derivados de evidencias; límites de coste cuadrático | 10 |
| R11 | Rúbricas y defensa | Evidencias ancladas y edición docente; sin calificación automática final | 11 |
| R12 | Informes y casos | PDF reproducible, historial de decisiones y apelaciones con permisos | 12 |
| R13 | Moodle 5.0.2 | Flujo real de entrega autorizada a informe y errores de sincronización | 13 |
| R14 | SaaS y API | Aislamiento, cuotas, idempotencia, webhooks firmados y administración | 14 |
| R15 | Calidad | Pruebas de seguridad, accesibilidad, recuperación y carga | 15 |
| R16 | Operación | Despliegue, backups restaurados, alertas y manuales verificados | 16 |

## Invariantes

Ningún hallazgo carece de evidencia y versión de motor. Similitud no significa plagio; patrones lingüísticos no demuestran autoría. No se inventan fuentes, porcentajes, historial ni métricas. Todo resultado declara fuentes intentadas, recuperadas, comparadas, fallos y exclusiones. Datos institucionales nunca se consultan entre tenants. Documento y fuentes son datos no confiables, incluso si contienen instrucciones para modelos.

## Parámetros iniciales propuestos

Carga máxima 25 MiB, PDF 300 páginas, DOCX 100 MiB descomprimidos y 2.000 entradas ZIP, máximo 100 documentos por lote. Son políticas iniciales configurables, no capacidades medidas. TXT UTF-8, con otros encodings rechazados explícitamente hasta admitirlos de forma comprobable. OCR opcional por idioma instalado. Retención inicial propuesta de 90 días para originales, configurable según contrato y legislación; no activar borrado antes de acordar política institucional y retenciones legales.

## Puerta de Fase 0

Documentación de arquitectura, contratos, datos, motores, UI, búsqueda, IA, seguridad, pruebas, roadmap, aceptación, riesgos, hardware y costes; evidencia de inspección y fuentes tecnológicas; commit local revisado. No exige construir la aplicación ni entrenar modelos. Compatibilidad integrada, licencias transitivas y seguridad de versiones son puertas de Fase 1, antes de instalar el stack de aplicación. Cada fase se presenta y se detiene hasta autorización.

## Aceptación final

Ejecutar una entrega real desde autenticación hasta informe, con extracción, coincidencias literales y semánticas, referencias verificadas, resaltados correctos, evidencias y revisión humana. Modelos con evaluación documentada; aislamiento probado, errores visibles y documentación de instalación reproducida. Las capacidades no disponibles impiden declarar el producto completo. El servicio de búsqueda general y el análisis de IA se muestran como no disponibles cuando falten proveedor autorizado o modelo aprobado.
