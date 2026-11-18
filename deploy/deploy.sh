#!/usr/bin/env bash
# Roda NA VM da Azure, chamado pelo pipeline via "az vm run-command" (sem SSH).
# Uso: ACR=acrxxx.azurecr.io IMAGE_TAG=<sha> KEYVAULT=kv-xxx ./deploy.sh
# Autenticação: identidade gerenciada da VM (token pedido ao IMDS), sem nenhuma senha em disco além do .env.
set -euo pipefail
cd "$(dirname "$0")"

: "${ACR:?}" "${IMAGE_TAG:?}" "${KEYVAULT:?}"
IMDS="http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01"

token() {
  curl -sSf -H "Metadata: true" "$IMDS&resource=$1" | jq -r .access_token
}

# --- segredos do Key Vault
KV_TOKEN=$(token "https://vault.azure.net")
segredo() {
  curl -sSf -H "Authorization: Bearer $KV_TOKEN" \
    "https://$KEYVAULT.vault.azure.net/secrets/$1?api-version=7.4" | jq -r .value
}

umask 077
cat > .env <<ENV
REGISTRY=$ACR
IMAGE_TAG=$IMAGE_TAG
DB_PASSWORD=$(segredo db-password)
METRICS_TOKEN=$(segredo metrics-token)
SITE_ADDRESS=$(segredo site-address)
CHAOS_ENABLED=$(segredo chaos-enabled)
ENV

# --- login no ACR com a identidade da VM (mesma troca que o "az acr login" faz)
ARM_TOKEN=$(token "https://management.azure.com/")
ACR_REFRESH=$(curl -sSf -X POST \
  --data-urlencode "grant_type=access_token" \
  --data-urlencode "service=$ACR" \
  --data-urlencode "access_token=$ARM_TOKEN" \
  "https://$ACR/oauth2/exchange" | jq -r .refresh_token)
echo "$ACR_REFRESH" | docker login "$ACR" -u 00000000-0000-0000-0000-000000000000 --password-stdin >/dev/null

# --- containers não podem falar com o IMDS (evita roubo do token da VM por SSRF)
iptables -C DOCKER-USER -d 169.254.169.254 -j DROP 2>/dev/null \
  || iptables -I DOCKER-USER -d 169.254.169.254 -j DROP

docker compose pull --quiet
# --wait só retorna quando todos os healthchecks estão verdes (senão o pipeline falha)
docker compose up -d --remove-orphans --wait --wait-timeout 300
docker image prune -af --filter "until=72h" >/dev/null || true
docker compose ps
echo "DEPLOY_OK $IMAGE_TAG"
