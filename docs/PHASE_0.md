# Entrega de Fase 0

Estado: investigación y diseño completados para revisión; implementación no iniciada. La arquitectura queda adoptada como base y las decisiones tecnológicas condicionadas tienen puertas explícitas antes de usar dependencias/modelos en producción. No existe validación integrada del stack; no se afirma producto funcional.

| Resultado solicitado | Documento |
|---|---|
| 1. Arquitectura | [ARCHITECTURE](../ARCHITECTURE.md) |
| 2. Stack y nivel de validación | [RESEARCH](RESEARCH.md) |
| 3. Carpetas | [ARCHITECTURE](../ARCHITECTURE.md) |
| 4. Modelo de datos | [DATABASE](../DATABASE.md) |
| 5. Motores | [AI_MODELS](../AI_MODELS.md), [API](../API.md) |
| 6. Búsqueda web | [AI_MODELS](../AI_MODELS.md) |
| 7. Análisis de IA | [AI_MODELS](../AI_MODELS.md), [EVALUATION](../EVALUATION.md) |
| 8. Visualizador | [UX](UX.md) |
| 9. Interfaces | [UX](UX.md) |
| 10. Seguridad | [SECURITY](../SECURITY.md) |
| 11. Pruebas | [EVALUATION](../EVALUATION.md) |
| 12. Hoja de ruta | [ROADMAP](../ROADMAP.md) |
| 13. Aceptación | [REQUIREMENTS](../REQUIREMENTS.md) |
| 14. Riesgos | [ROADMAP](../ROADMAP.md) |
| 15. Hardware | [DEPLOYMENT](../DEPLOYMENT.md) |
| 16. Costes y dependencias | [DEPLOYMENT](../DEPLOYMENT.md) |

## Comprobaciones realizadas

- Repositorio inspeccionado, sin archivos de aplicación ni commits previos; no se hallaron instrucciones AGENTS.md en el workspace.
- Herramientas y límites cgroup inspeccionados: Python 3.12.14, Node 24.19.0, npm 11.9.0, cliente Docker 28.4.0; cuota 4 CPU/32 GiB RAM.
- 23 metadatos de versiones y 7 fuentes adicionales recuperados por HTTPS con TLS habilitado, incluidos tag Moodle 5.0.2 y alternativas PDF. URLs y respuestas retenidas, hashes comprobados.
- Documentos obligatorios, enlaces locales y cierre de bloques Markdown verificados automáticamente; diferencias revisadas con Git.
- No ejecutadas pruebas de aplicación, modelos, Docker daemon, BD, Windows, Moodle operativo ni proveedores bibliográficos. No hay precisión/rendimiento medidos.

## Decisiones abiertas con puerta explícita

Resolver versiones mantenidas y avisos de seguridad, elegir release/licencia de Redis y revisar licencias transitivas del extractor antes del lock de Fase 1. Validar geometría en Fase 2, proveedor de búsqueda autorizado en Fase 3, modelos/licencias/evaluación en Fases 5 y 8. Política legal y retención, presupuesto y volumen reales se necesitan antes del piloto. No se requieren secretos para continuar el diseño.

No se inicia Fase 1, no se hace push y no se modifica/publica la configuración del entorno. Próximo paso, sujeto a autorización: infraestructura, lockfiles y revisión de licencias, autenticación/roles y layout con pruebas reales.
