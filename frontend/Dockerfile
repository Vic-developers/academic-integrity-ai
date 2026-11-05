# syntax=docker/dockerfile:1
FROM node:24-alpine@sha256:8a32c8cf649a49915a66e81e7a609223c708d0adabf288ee3f4077d765542f85 AS build
WORKDIR /app
RUN --mount=type=bind,source=.,target=/src,readonly --mount=type=secret,id=proxy_ca --mount=type=tmpfs,target=/build \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    cp -R /src/. /build/ && cd /build && npm ci --cache /build/.npm --strict-ssl=true && npm run build && cp -R dist /app/dist
FROM nginxinc/nginx-unprivileged:1.28-alpine@sha256:7377697a821c131a924a7105fafbe7414db4e9fcc77a6f08f776f33f141ec3f8
COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
