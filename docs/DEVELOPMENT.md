# Desarrollo y pruebas — Fase 1

## Alcance

Compose es un entorno de desarrollo con cookies HTTP locales y Mailpit; no es un despliegue de producción. El backend valida configuración de producción: exige origen HTTPS, cookie Secure y SMTP STARTTLS. Producción requiere además proxy TLS, secretos gestionados, backups restaurados y auditorías de Fases 15–16.

API y worker usan `aid_app` sin superusuario ni BYPASSRLS. Migraciones y CLI usan `aid_owner` y no deben exponerse por HTTP. Las tablas de identidad global (users/sessions/reset_tokens/email_jobs) son una frontera de confianza interna: solo servicios de identidad las consultan. Instituciones, membresías y actividad tienen RLS forzada. Las FK de actividad impiden relacionar actores de otra institución. Los módulos futuros deben mantener la misma separación y añadir sus propias políticas.

## Instalación local con Docker

`python scripts/configure_dev.py` genera `.env` una sola vez. `docker compose up --build -d` construye frontend/backend, espera PostgreSQL/Redis, ejecuta Alembic y arranca servicios. No se descarga ningún modelo IA ni se requiere GPU. El primer volumen de PostgreSQL ejecuta `infra/init-db.sh`; conservar sus permisos de lectura/ejecución (Git registra executable). No borrar volúmenes para resolver errores sin respaldo y autorización.

El frontend compilado se sirve con Nginx sin root y comunica con API por red interna. Solo Nginx debe acceder a API: Compose confía en su cabecera X-Forwarded-For sobrescrita para limitar por IP real. No publicar el puerto de API con esa configuración de confianza. El comando de desarrollo directo de Uvicorn desactiva proxy headers.

El worker usa un proceso de concurrencia 1 y scheduler embebido, apropiado para esta fase local; separar el scheduler único antes de escalar en producción. PostgreSQL conserva los correos pendientes aunque Redis se reinicie. Envíos fallidos tienen como máximo tres intentos; inspeccionar estado sin registrar destinatarios ni enlaces en logs. Solo se guardan hashes de sesión/reset; el token de recuperación se genera al entregar y no se persiste en claro. SMTP no participa en una transacción distribuida: una caída después del envío y antes del commit puede entregar un enlace inválido. Se debe solicitar otro correo en ese caso, sin afirmar entrega exactamente una vez.

## Pruebas desde el host (Linux/WSL)

Python 3.12, Node 24 y Docker Compose v2:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements-dev.lock
npm ci --prefix frontend
python3.12 scripts/configure_dev.py
# Omitir el comando anterior si ya existe .env.
docker compose -f compose.yaml -f infra/compose.test-access.yaml up -d --wait db redis mailpit
.venv/bin/python scripts/test_backend.py
npm run build --prefix frontend
docker compose build
cd frontend
npx playwright install chromium
cd ..
.venv/bin/python scripts/run_e2e.py
```

En Windows, el venv usa `.venv\Scripts\python.exe`. Se recomienda ejecutar la suite completa dentro de WSL2; aún no se ha verificado esa plataforma. Los tres puertos opcionales de pruebas están limitados a loopback: PostgreSQL 55432, Redis 56379 y SMTP 51025. `.env.example` debe alinearse con esos puertos o usar el generador.

`test_backend.py` crea únicamente `aid_test` en la instancia local usando credenciales del migrador; migra el esquema y ejecuta pytest. Redis usa DB 15 exclusivamente para tests; DB 0 queda para desarrollo. Los fixtures rechazan otra base o DB Redis. No ejecutar en infraestructura institucional. `run_e2e.py` prepara datos sintéticos en aid_test, recrea temporalmente API/worker contra esa base, ejecuta Playwright y restaura los servicios a desarrollo incluso si falla la prueba. No ejecutar suites simultáneamente ni durante trabajo de otra persona. No hay cuentas de prueba en la base de desarrollo final.

Si Chromium ya existe: `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium .venv/bin/python scripts/run_e2e.py`. Las pruebas usan servicios reales; ninguna respuesta del producto está interceptada o simulada.

## Comprobaciones y dependencias

```bash
.venv/bin/ruff check backend scripts
npm run build --prefix frontend
.venv/bin/pip-audit -r backend/requirements.lock --disable-pip --no-deps
npm audit --prefix frontend --audit-level=low
```

Locks Python con hashes; npm ci respeta package-lock.json. Revisar licencias declaradas y notices de todas las dependencias antes de distribuir imágenes. Psycopg/psycopg-binary son LGPL-3.0-only: conservar atribución, licencia y obligaciones de distribución. Las dependencias frontend incluyen MPL-2.0 y datos CC-BY-4.0: conservar sus atribuciones y revisar obligaciones si se distribuyen o modifican. Redis 8 ofrece opciones AGPLv3/RSALv2/SSPLv1; no asumir BSD. El servidor se usa sin modificar y separado de la aplicación; revisar las obligaciones de la opción elegida para la distribución comercial. PostgreSQL/pgvector no añaden coste de licencia. No se incluyeron PyMuPDF ni modelos cuyo uso comercial no se haya evaluado.

`infra/compose.cloud-build.yaml` monta el CA público del entorno únicamente durante instalaciones Docker. Se usa con `docker compose -f compose.yaml -f infra/compose.cloud-build.yaml build`. Preservar los proxies heredados; no desactivar TLS. Si el builder necesita escribir en un home de solo lectura, configurar `BUILDX_CONFIG` en un directorio temporal escribible sin cambiar DOCKER_CONFIG ni credenciales.

La workflow de GitHub Actions está preparada, pero no ejecutada remotamente en esta sesión. Solo publica comprobaciones, nunca despliega. Los resultados locales no equivalen a un CI remoto exitoso.
