# Hoja de ruta y riesgos

## Fase 7 — Afirmaciones y evaluación humana

Se verifica el flujo local de fase 7: candidatas heurísticas, pasajes léxicos, selección manual y evaluación humana trazable. La puerta completa de clasificación automática/NLI y recuperación externa queda pendiente, junto a los pendientes previos de semántica y proveedores. No se avanza a fase 8. [Alcance detallado](docs/PHASE_7.md).

## Fase 6 — Bibliografía local y adaptadores de metadatos

Se implementó el flujo local de fase 6: extracción, patrones de cita, duplicados, trabajos durables, permisos, vista y exportación. Los adaptadores Crossref/OpenAlex se prueban con fixtures de contrato; las dos consultas reales al origen fallaron por la política de red. La puerta de verificación en línea sigue pendiente. No se ha comenzado la fase 7; semántica permanece pospuesta. [Estado detallado](docs/PHASE_6.md).

## Continuación sin Hugging Face — Infraestructura vectorial

Decisión: omitir Hugging Face. La parte independiente de la fase 5 implementa persistencia y recuperación matemática en pgvector, con permisos y borrado probados. Inferencia multilingüe, calibración y hallazgos semánticos permanecen pospuestos. No se ha iniciado la fase 6. [Resultado](docs/PHASE_5_VECTOR.md).

## Fase 5 iniciada — Pendiente de verificar el modelo

El origen de pesos multilingües está bloqueado por el proxy. Instalador, integridad y fragmentación preparados; inferencia, evaluación independiente y pgvector aún no integrados ni activados. [Estado real](docs/PHASE_5_PREPARATION.md). La siguiente puerta es verificar el modelo, no comenzar la fase 6.

## Antecedente — Fase 4

Fase 4 implementada: visor, resaltado verificable, navegación, explicación, revisión humana y pruebas. [Alcance](docs/PHASE_4.md). Fase 5 (similitud semántica) no iniciada; requiere autorización.

## Antecedente — Fase 3

Fase 3 implementada: comparación literal institucional explícita y limitación web visible. [Resultados y límites](docs/PHASE_3.md). La fase 4 (visor de evidencias y resaltado exacto) no se ha iniciado y requiere autorización.


## Antecedente histórico — Fase 2

Fase 2 entregada para revisión: carga, almacenamiento, extracción y visualizador básico reales. Fase 3 permanece pendiente de autorización. Ver [PHASE_2](docs/PHASE_2.md).

## Antecedente histórico — cierre de Fase 1

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
