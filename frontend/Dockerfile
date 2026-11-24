# syntax=docker/dockerfile:1
# ---------- estágio 1: dependências ----------
# nosemgrep: dockerfile-source-not-pinned -- tag oficial; o build usa --pull e o Trivy escaneia a imagem final a cada commit (Dependabot atualiza)
FROM node:25-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---------- estágio 2: build ----------
# nosemgrep: dockerfile-source-not-pinned -- tag oficial; o build usa --pull e o Trivy escaneia a imagem final a cada commit (Dependabot atualiza)
FROM node:25-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---------- estágio 3: imagem final (só o servidor standalone) ----------
# nosemgrep: dockerfile-source-not-pinned -- tag oficial; o build usa --pull e o Trivy escaneia a imagem final a cada commit (Dependabot atualiza)
FROM node:25-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
# npm, npx, corepack e yarn não são usados em produção: removidos (menos CVEs no Trivy)
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
           /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
           /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-*
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
# usuário "node" (uid 1000) já existe na imagem oficial e não é root
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "server.js"]
