#!/usr/bin/env bash
# Gera prometheus/prometheus.yml e prometheus/metrics_token.
# Sem argumentos: lê o alvo do "terraform output" e o token do Key Vault (precisa do "az login").
# Com argumentos: ./configurar.sh <alvo> <token>     ex.: ./configurar.sh 3-91-10-20.sslip.io:443 abc123
set -euo pipefail
cd "$(dirname "$0")"

if [ $# -ge 2 ]; then
  ALVO="$1"; TOKEN="$2"
else
  ALVO=$(terraform -chdir=../infra output -raw metrics_target)
  TOKEN=$(eval "$(terraform -chdir=../infra output -raw comando_token_metricas)")
fi

case "$ALVO" in *:443) ESQUEMA=https ;; *) ESQUEMA=http ;; esac

sed -e "s|__ALVO__|$ALVO|" -e "s|__ESQUEMA__|$ESQUEMA|" prometheus/prometheus.yml.modelo > prometheus/prometheus.yml
umask 077
printf '%s' "$TOKEN" > prometheus/metrics_token
chmod 644 prometheus/metrics_token # o container do Prometheus roda como "nobody" e precisa ler
echo "Prometheus vai coletar $ESQUEMA://$ALVO/api/metrics"
echo "Agora: docker compose up -d   (ou: curl -X POST localhost:9090/-/reload se já estiver rodando)"
