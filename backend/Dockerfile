# syntax=docker/dockerfile:1
FROM python:3.12-alpine@sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8
RUN --mount=type=bind,source=.,target=/src,readonly --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir --require-hashes -r /src/requirements.lock && \
    adduser -D -u 10001 app && mkdir /app && cp -R /src/. /app/ && chown -R app:app /app
WORKDIR /app
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-access-log"]
