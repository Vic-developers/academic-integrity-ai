# Hoja de ruta y riesgos

## Estado al cierre de Fase 1

Fase 1 implementada y comprobada: consultar [PHASE_1](docs/PHASE_1.md). Fase 2 no iniciada y pendiente de autorización. Esta hoja conserva las puertas de las fases futuras.

Cada fase requiere objetivos, archivos reales, pruebas aplicables, correcciones, seguridad, documentación, revisión de diferencias y commit local. Push solo con autorización; ninguna publicación de entorno o producto implícita. Al presentar cada fase se espera permiso para la siguiente. No declarar finalización si persisten fallos críticos.

| Fase | Entregable y puerta de salida |
|---|---|
| 0 | Arquitectura, contratos, investigación, datos, riesgos y criterios documentados; sin implementación |
| 1 | Stack bloqueado y licencias revisadas, Compose probado, sesión/recuperación/roles y aislamiento básico, layout real |
| 2 | Archivos reales validados, originales privados, extracción y mapas con pruebas; OCR explícitamente opcional |
| 3 | Índice literal institucional y proveedor web autorizado o limitación explícita; evaluación de rangos/fuentes |
| 4 | Visor de dos paneles con evidencias reales y pruebas de geometría/Unicode |
| 5 | Modelo semántico aprobado, vectores por tenant, calibración y evaluación por idioma |
| 6 | Crossref/OpenAlex consultados realmente, referencias y diferencias trazables |
| 7 | Afirmaciones con pasajes verificables y abstención evaluada |
| 8 | Datos autorizados, baseline, separación rigurosa, evaluación/calibración y abstención |
| 9 | Forense observado y estilo con autorización, incertidumbre y muestras suficientes |
| 10 | Matriz/grafo con índices y carga medidos, sin inferencia de colaboración indebida |
| 11 | Rúbricas y defensa con evidencia, edición y decisión docente |
| 12 | Casos, comentarios, apelaciones, decisiones e informes PDF verificables |
| 13 | Integración Moodle 5.0.2 probada y plugin si hace falta |
| 14 | Administración SaaS, cuotas, webhooks y API de servicio; controles tenant reforzados |
| 15 | Seguridad, carga, accesibilidad y recuperación sin fallos críticos |
| 16 | Imágenes producción, restore probado, manuales reales y preparación de despliegue |

El aislamiento multiinstitucional se construye desde Fase 1; Fase 14 amplía administración, no pospone la seguridad. Los informes operan sobre versiones de evidencia desde Fase 3 aunque la exportación llegue después. No se estiman fechas sin equipo, corpus, presupuesto y volumen institucional.

## Registro de riesgos

| Riesgo | Impacto | Mitigación / responsable funcional / puerta |
|---|---|---|
| Cobertura web limitada o acceso prohibido | Fuentes omitidas | Arquitectura de proveedores y cobertura visible; integraciones; F3 |
| Falsos positivos IA y sesgo en español | Daño académico | Evaluación por grupo y abstención; ML y evaluación; F8 |
| Mapas PDF inexactos/OCR | Evidencia mal ubicada | Cajas/palabras y fixtures; documental/QA; F2–4 |
| Licencias AGPL/modelos/datos | Restricción comercial | Alternativa PDF permisiva, revisión de notices y artefactos; arquitectura/legal; F1/F5 |
| Fuga entre tenants | Exposición de datos | RLS, FK, tests de rutas y jobs; seguridad/backend; desde F1 |
| SSRF y archivos hostiles | Compromiso de red/recursos | Pasarela, sandbox, límites; seguridad/infra; F2–3 |
| Pérdida/duplicación de jobs | Resultados corruptos | Outbox, leases e idempotencia; backend; F1–3 |
| Saturación CPU/GPU y N² pares | Coste y colas | Índices, cuotas y backpressure; datos/infra; F5/F10 |
| Fuentes retiradas y copyright | Evidencia incompleta | Snapshots según permiso y estado de acceso; integraciones; F3/F6 |
| Dependencias antiguas o vulnerables | Riesgo operativo | Resolver versiones mantenidas, SBOM y escáner antes del lock; DevOps; F1 |
| APIs Moodle insuficientes | Integración incompleta | Plugin y pruebas de versión; LMS; F13 |
| Retención/consentimiento sin definir | Riesgo legal | Políticas institucionales y borrado probado; producto/privacidad; antes del piloto |

Roles son responsabilidades a asignar, no personas contratadas ni revisión legal realizada.
