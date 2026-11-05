# Seguridad y privacidad

## Estado actual — Fase 3

Auditorías verifican acceso al principal y todas las fuentes al crear, ejecutar y leer; revocación oculta el resultado y borrado invalida/limpia derivados. Idempotencia concurrente, RLS, límites de texto/evidencia/CPU y cancelación probados. No hay fetch de URL ni acceso web activo. Persisten las limitaciones de aislamiento del parser descritas en Fase 2.


## Antecedente histórico — Fase 2

Fase 2 agrega originales privados 0400, rollback de archivos ante fallo de commit, RLS/propietario/asignatura, validación de formatos/ZIP/XML, subproceso sin secretos y filtros seccomp. La contención completa de filesystem y antivirus no están implementados; antes de producción son puertas explícitas. Ver [Fase 2](docs/PHASE_2.md) para el alcance real y la corrección de PDF.js.

## Antecedente histórico — cierre de Fase 1

Controles de acceso de Fase 1 implementados y probados: Argon2id, sesión hash, CSRF/Origin, rate limit compartido con bloqueo si Redis falla, RLS y FK tenant. Revisar [DEVELOPMENT](docs/DEVELOPMENT.md) para la confianza del proxy y frontera de identidad. MFA, archivos/SSRF, backups y auditoría de producción siguen como diseño para sus fases; no se presentan como controles ejecutados.

Diseño de controles y pruebas; no es una auditoría de un sistema implementado. Documentos académicos son contenido no confiable. Ninguna instrucción embebida controla herramientas, autorización o prompts del sistema.

## Amenazas y controles

| Amenaza | Control y verificación prevista |
|---|---|
| Acceso entre instituciones/IDOR | Membresía validada, FK compuestas, RLS forzada, almacenamiento privado; pruebas cruzadas en todas las rutas y workers |
| Robo de sesión | Contraseñas Argon2id con parámetros medidos, tokens opacos aleatorios con hash en BD; cookie HttpOnly, Secure, SameSite=Lax; expiración y revocación |
| CSRF/XSS | Token CSRF y validación Origin en mutaciones con cookie; CSP, escape React, no HTML de documentos sin saneamiento; CORS por origen concreto |
| Fuerza bruta | Rate limit por cuenta/IP/tenant, mensajes uniformes y auditoría sin contraseña; recuperación por token de uso único |
| ZIP bombs, PDF malicioso | Validación de firma y parser, extensión como dato secundario; ZIP limitado sin extracción de rutas; parser sin red, CPU/RAM/tiempo limitados, usuario no root |
| Malware | Cuarentena y escaneo abierto cuando esté desplegado; si la política exige escaneo, su ausencia bloquea publicación del documento |
| SSRF y rebinding | Solo HTTPS, destinos autorizados, sin userinfo; bloquear loopback, privadas, link-local, metadata, IPv6 reservado y puertos no admitidos; validar DNS y cada redirección |
| SQL injection | SQLAlchemy parametrizado, sin SQL construido con datos del documento; rol mínimo y migraciones separadas |
| Abuso de recursos | Cuotas atómicas, backpressure, límites por tenant y colas separadas; cancelación y leases |
| Fuga en logs/modelos | No registrar texto/tokens, redacción y control de acceso; inferencia local, datasets autorizados y sin entrenamiento con entregas por defecto |
| Cadena de suministro | Locks con hashes, SBOM, licencias transitivas, escáner de vulnerabilidades y revisión antes de desplegar |

La protección SSRF debe funcionar con el proxy heredado: si la aplicación no puede validar el IP realmente utilizado, la pasarela/proxy debe imponer restricciones de red y destinos. No basta resolver DNS en la aplicación y luego permitir una resolución distinta. No eludir el proxy ni desactivar TLS. Fetchers no reciben cookies de usuario ni cabeceras de autenticación del servicio. El usuario nunca puede hacer que una URL pública acceda a almacenamiento institucional.

## Sesiones y permisos

Login con institución seleccionada solo entre membresías activas. Reautenticación para operaciones sensibles y MFA planificada para administradores. Recuperación por correo mediante transporte configurable, sin cuentas/contraseñas por defecto. Entorno de desarrollo puede usar buzón local explícito; producción necesita SMTP autorizado. Sesión cambia al elevar privilegios; cierre y cambio de contraseña revocan sesiones conforme a política. Acceso excepcional de soporte requiere motivo, aprobación institucional y registro.

## Privacidad operativa

Recoger mínimos datos, base jurídica y consentimiento cuando corresponda. No indexar trabajos para otras instituciones ni enviarlos a proveedores externos sin autorización. Las consultas web revelan fragmentos: opción institucional desactivada por defecto hasta aceptar alcance, términos y tratamiento de datos. Cifrado TLS en tránsito y volumen/objetos cifrados en producción; claves gestionadas externamente. URLs firmadas de corta duración sin incluirlas en logs. Copias, exportaciones, informes y borrado siguen la misma política que el original.

## Puertas de salida

Antes de producción: aislamiento y permisos sin fallos críticos, revisión de amenazas, análisis de dependencias/licencias, prueba de restauración, política de incidentes y retención, accesibilidad y pentest del flujo de archivos y recuperación. Canal de reporte privado por definir por la institución operadora antes de exposición pública; no inventar dirección de contacto.
