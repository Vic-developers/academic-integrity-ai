# Fase 1 — Infraestructura y autenticación

Fecha: 5 de noviembre de 2026. Alcance autorizado: exclusivamente Fase 1. La arquitectura de Fase 0 se mantiene; no se implementan motores ni carga documental.

## Implementación

- Backend FastAPI con Pydantic, SQLAlchemy y primera migración Alembic congelada; OpenAPI real en `/api/openapi.json`.
- PostgreSQL 16/pgvector, rol migrador separado del rol HTTP sin superusuario ni BYPASSRLS. RLS forzada para instituciones, membresías y actividad; contexto por transacción, nunca persistido en el pool.
- Contraseñas Argon2id; sesiones opacas con hash, caducidad, rotación y revocación. Cookies HttpOnly/SameSite y Secure configurable; validación de Origin, cabecera de solicitud y CSRF ligado a sesión para mutaciones autenticadas.
- Recuperación por tokens con hash, caducidad y uso único; cambio de contraseña revoca sesiones y enlaces anteriores. Bloqueos serializan cambios concurrentes.
- Cola durable de correo en PostgreSQL, worker Celery/Redis y SMTP real. Mailpit solo en desarrollo. Entrega al menos una vez con limitaciones SMTP documentadas, sin prometer transacciones distribuidas.
- Seis roles con permisos del servidor. CLI interactiva para primera institución/administrador, y superadministrador opcional por operador; ninguna cuenta predeterminada.
- Frontend React, TypeScript estricto, Vite, Tailwind, React Router, TanStack Query, React Hook Form y Zod. Páginas/componentes separados, login, recuperación, institución, resumen, usuarios paginados y actividad. Modo claro/oscuro, responsive, foco visible y navegación por teclado.
- Métricas de miembros consultadas realmente; funciones documentales futuras declaradas como no disponibles.
- Compose local, imágenes base fijadas por digest, locks Python con hashes y npm lock, scripts reproducibles y workflow CI sin despliegue.

## Evidencia real

| Comprobación | Resultado |
|---|---|
| Integración Python con PostgreSQL/Redis/SMTP reales | 22 pruebas aprobadas; permisos de los seis roles, RLS, CSRF, revocación, recuperación, concurrencia de token y CLI |
| Playwright en Chromium del sistema | 2 recorridos aprobados: acceso/usuarios/tema/móvil/logout y recuperación Celery+SMTP/rol docente |
| TypeScript estricto y build Vite | Aprobados |
| Ruff | Aprobado |
| Imágenes backend y frontend | Construidas con TLS y CA del entorno; procesos sin root |
| Bootstrap de PostgreSQL vacío | init-db, rol restringido, extensión vector y migración comprobados desde almacenamiento temporal vacío; volumen original preservado |
| Disponibilidad | `/api/health/ready` devuelve estado ready con esquema y Redis presentes |
| Auditoría de paquetes Python | 43 dependencias de ejecución; 0 vulnerabilidades conocidas reportadas en la consulta |
| Auditoría npm | 0 vulnerabilidades conocidas reportadas en la consulta |
| Licencias y SBOM | Metadatos Python y lock npm conservados, SBOM frontend desde lock; obligaciones LGPL/Redis documentadas |

Estos conteos son de pruebas técnicas, no métricas científicas de detección. Las fixtures son sintéticas, identificadas como pruebas y limitadas a aid_test/Redis DB 15. No se utilizaron mocks para producir respuestas del producto. La prueba CLI sustituye solo la entrada interactiva de contraseña, con persistencia y login reales.

Una advertencia de deprecación de Starlette recomienda httpx2 para TestClient; las pruebas pasan con httpx actual. Vite elimina dos comentarios de anotación de Zod al compilar; no impiden el build. No se afirma ausencia total de vulnerabilidades: los escáneres no sustituyen auditoría ni cubren por sí solos todos los paquetes del sistema de las imágenes.

## Recursos y correcciones

Entorno CPU con cgroup 2 CPU/8 GiB RAM y filesystem de aproximadamente 8 GiB. Las capas/cachés Docker agotaron inicialmente el disco. Se recuperó espacio eliminando solo cachés/contenedores de esta tarea y trasladando dependencias temporales a /tmp. Se probó una compactación temporal de imagen; las imágenes finales se reconstruyeron desde Dockerfiles, sin depender de esa adaptación. La instalación frontend usa tmpfs durante npm ci/build para reducir disco temporal.

El arranque real reveló dependencias Redis incompletas en Celery y permisos de lectura de Nginx/init-db. Se corrigieron mediante celery[redis], ownership de configuración y permisos del script. Se corrigió también el orden de bloqueos del worker para alinearlo con la recuperación de contraseña. Las comprobaciones de esta entrega corresponden al código final, no a los primeros intentos fallidos.

## Límites y pasos siguientes

Windows/WSL2, SMTP de producción y GitHub Actions remoto aún no ejecutados. La configuración Compose es de desarrollo y no incluye TLS público ni garantías de producción. Antes del piloto: verificar obligaciones de distribución, invitaciones para identidades existentes, políticas institucionales y controles operativos. El alta administrativa inicial no adjunta automáticamente identidades de otras instituciones ni modifica sus contraseñas; el conflicto de correo existente requiere intervención del operador. La administración completa de instituciones, invitaciones y cuotas pertenece a Fase 14.

No hay procesamiento PDF/DOCX/TXT, modelos aprobados, búsquedas web, informes ni integración Moodle. No se han publicado cambios remotos ni un sitio. No se declara el producto completo.

Instalación y pruebas: [DEVELOPMENT](DEVELOPMENT.md), [README](../README.md). Ver [evidencias](validation/README.md). La Fase 2 requiere autorización expresa.
