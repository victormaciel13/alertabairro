# syntax=docker/dockerfile:1
# ---------- estágio 1: instala dependências ----------
# nosemgrep: dockerfile-source-not-pinned -- tag oficial; o build usa --pull e o Trivy escaneia a imagem final a cada commit (Dependabot atualiza)
FROM python:3.13-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---------- estágio 2: imagem final, sem ferramentas de build ----------
# nosemgrep: dockerfile-source-not-pinned -- tag oficial; o build usa --pull e o Trivy escaneia a imagem final a cada commit (Dependabot atualiza)
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# remove o pip da imagem final (menos superfície de ataque e menos CVEs) e cria usuário sem privilégios
RUN python -m pip uninstall -y pip \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder /install /usr/local
WORKDIR /app
# código pertence ao root e é só leitura para o usuário da aplicação
COPY app ./app
COPY models ./models
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
# 1 worker: com vários processos cada um teria o próprio contador do Prometheus
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
