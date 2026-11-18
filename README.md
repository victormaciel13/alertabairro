# AlertaBairro

Plataforma colaborativa de alertas de alagamento em São Paulo: o morador envia um relato com foto, um modelo YOLO11 confirma se há água na via e o relato aparece com o selo "verificado por imagem".

Global Solution 2026.2 · FIAP · CitizenTech · Secure DevOps Tools & Cloud Computing (Deploy Blindado)

## Ficha Técnica do MVP

| Item | Descrição |
|---|---|
| **Nome** | AlertaBairro |
| **Problema** | Em dias de chuva forte, moradores de São Paulo não têm informação local e confiável sobre ruas alagadas. |
| **Público** | Moradores, motoristas e entregadores das regiões que alagam com frequência. |
| **Solução** | Mapa colaborativo de relatos de alagamento; fotos enviadas são verificadas por visão computacional (YOLO11). |
| **URL pública** | https://alertabairro-8s16x.eastus.cloudapp.azure.com |
| **Front-end** | Next.js 16 |
| **Back-end** | Python 3.13, FastAPI, onnxruntime |
| **Banco** | PostgreSQL 16 + PostGIS |
| **Nuvem** | Microsoft Azure (VM Linux, Container Registry, Key Vault), criada por Terraform |
| **CI/CD** | GitHub Actions: build, testes, Gitleaks, Semgrep, Trivy, deploy automático |
| **Observabilidade** | Prometheus + Grafana (4 sinais de ouro) e alertas |
| **Custo estimado** | ≈ US$ 41/mês (detalhado em [docs/arquitetura.md](docs/arquitetura.md#5-estimativa-de-custo-mensal-east-us-pagamento-conforme-o-uso)) |

**Integrantes**

| Nome | RM |
|---|---|
| Victor Camargo Maciel | 98384 |
| Geovanna Silva Cunha | 97736 |
| Pedro Emereci Gava | 551043 |
| Bianca Carvalho Dancs Firsoff | 551645 |

## Onde está cada critério da avaliação

| Critério | Onde ver |
|---|---|
| Dockerfile enxuto, não root, sem segredo | [backend/Dockerfile](backend/Dockerfile), [frontend/Dockerfile](frontend/Dockerfile) (multi-stage, `USER` sem privilégio) |
| Stack com docker compose | [docker-compose.yml](docker-compose.yml) (local) e [deploy/docker-compose.yml](deploy/docker-compose.yml) (produção) |
| Nuvem por Terraform, state e .tfvars fora do repo | [infra/](infra/) e [.gitignore](.gitignore) |
| Porta admin nunca aberta para 0.0.0.0/0 | [infra/network.tf](infra/network.tf): NSG só com 80/443, regra explícita bloqueando o resto (inclusive 22) |
| Pipeline com build, Gitleaks, Semgrep e Trivy a cada push | [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) |
| Segredos em GitHub Secrets e deploy automático | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` e `AZURE_SUBSCRIPTION_ID` em Secrets; login por OIDC (sem senha); deploy na `main` |
| Execução barrada e corrigida | seção [Evidência obrigatória](#evidência-obrigatória-segredo-barrado-pelo-pipeline) |
| Dashboard com 4 sinais de ouro e alerta | [observability/](observability/) |
| Arquitetura, responsabilidade compartilhada, LGPD e custo | [docs/arquitetura.md](docs/arquitetura.md) |

## Estrutura

```
backend/         FastAPI + YOLO (ONNX) + PostGIS          → imagem alertabairro-api
frontend/        Next.js                                   → imagem alertabairro-web
deploy/          docker compose de produção, Caddyfile e deploy.sh (rodam na VM)
infra/           Terraform Azure (VNet, NSG, VM, ACR, Key Vault, OIDC do GitHub)
observability/   Prometheus + Grafana locais, alertas e teste de carga (k6)
docs/            arquitetura, responsabilidade compartilhada, LGPD e custos
.github/         pipeline CI/CD e Dependabot
```

Rotas da API (atrás do proxy, com prefixo `/api`): `GET /health`, `GET /relatos`, `POST /relatos`, `POST /relatos/foto`, `GET /metrics` (com token) e a documentação em `/api/docs`.

---

## Passo a passo do deploy (Azure)

### 0. Pré-requisitos
- Assinatura **Azure for Students** ativa (https://azure.microsoft.com/free/students, com o e-mail da FIAP; não pede cartão).
- No computador: Azure CLI, Terraform e Git. No Windows:
  ```bash
  winget install Microsoft.AzureCLI
  winget install Hashicorp.Terraform
  ```
- Login (abre o navegador; entre com o e-mail da FIAP):
  ```bash
  az login
  az account show --query "{assinatura:name, id:id}" -o table
  ```

### 1. Descobrir as regiões liberadas para você
O Azure for Students só deixa criar recursos em algumas regiões, e a lista muda de aluno para aluno:
```bash
az policy assignment list --query "[?contains(displayName,'region') || contains(displayName,'location')].parameters" -o json
```
Escolha uma região da lista (de preferência `eastus`, `eastus2` ou `westus2`, que são mais baratas). Se o comando não mostrar nada, abra no portal **Policy → Assignments → Allowed resource deployment regions**.

### 2. Colocar o modelo de visão
No Colab, exporte o modelo vencedor para ONNX:
```python
!pip install -q ultralytics onnx
from ultralytics import YOLO
YOLO("/content/drive/MyDrive/alertabairro/runs/v1_baseline/weights/best.pt").export(format="onnx", imgsz=640)
```
Renomeie o arquivo gerado para `alertabairro_v1.onnx` e coloque em `backend/models/` (≈ 10 MB, pode ir direto para o Git).

### 3. Criar a infraestrutura
Registre uma vez os serviços que o projeto usa (no PowerShell):
```powershell
foreach ($p in "Microsoft.Compute","Microsoft.Network","Microsoft.Storage","Microsoft.ContainerRegistry","Microsoft.KeyVault","Microsoft.ManagedIdentity") { az provider register --namespace $p }
```
Espere uns minutos até todos ficarem `Registered`:
```powershell
az provider list --query "[?contains('Microsoft.Compute Microsoft.Network Microsoft.Storage Microsoft.ContainerRegistry Microsoft.KeyVault Microsoft.ManagedIdentity', namespace)].{servico:namespace, estado:registrationState}" -o table
```
Depois:
```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # preencha subscription_id, localizacao e github_repo
terraform init
terraform apply
```
Leva uns 5 minutos. Depois disso, a VM ainda leva uns 3 minutos para instalar o Docker.

Se aparecer **RequestDisallowedByAzure**, a região não está liberada: troque `localizacao` e rode `terraform apply` de novo. Se a VM der erro de **SkuNotAvailable**, troque `vm_size` por outro tamanho com `None` em `az vm list-skus --location eastus --size Standard_B2 --all -o table`.

### 4. Configurar o GitHub
```bash
terraform output github_variaveis
```
Em **Settings → Secrets and variables → Actions**:
- aba **Secrets**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` e `AZURE_SUBSCRIPTION_ID`;
- aba **Variables**: `RESOURCE_GROUP`, `VM_NAME`, `ACR_NAME`, `KEY_VAULT` e `APP_URL`.

Nenhum desses valores é uma senha: o GitHub entra na Azure por OIDC e recebe um token temporário a cada execução, e a identidade só aceita a branch `main` e o ambiente `producao` deste repositório.

### 5. Push
```bash
git push origin main
```
O pipeline roda a cada push, em qualquer branch: Gitleaks, Semgrep, testes e Terraform+Trivy em paralelo, depois build e Trivy nas imagens. Só na `main` ele continua com push no ACR e deploy na VM pelo Run Command da Azure (sem SSH). No fim, o teste de fumaça chama `APP_URL/api/health`.

Se o primeiro deploy falhar com erro de autorização, as permissões ainda estão propagando na Azure: espere 5 minutos e clique em **Re-run failed jobs**.

---

## Evidência obrigatória: segredo barrado pelo pipeline

1. Crie um arquivo com uma chave **falsa** (o comando monta a chave em duas partes para ela não aparecer neste README):
   ```bash
   printf 'AWS_ACCESS_KEY_ID="%s%s"\n' AKIAQ3EGRZ7X KMPLNTWB > backend/app/config_teste.py
   git add . && git commit -m "teste: segredo falso" && git push
   ```
   📸 Print do job **Segredos (Gitleaks)** vermelho com `RuleID: aws-access-token` e do deploy que não rodou.
2. Corrija:
   ```bash
   git rm backend/app/config_teste.py && git commit -m "remove segredo de teste" && git push
   ```
   📸 Print do pipeline todo verde.

O Gitleaks analisa só os commits de cada push, por isso a correção passa. Com uma chave real, além de remover seria obrigatório **revogar a chave**, porque ela continua no histórico.

---

## Observabilidade (Prometheus + Grafana locais)

```bash
cd observability
./configurar.sh            # lê o alvo do terraform e o token do Key Vault
docker compose up -d
```
- Grafana: http://localhost:3001 (admin / `troque-no-primeiro-login`) → pasta **AlertaBairro** → dashboard **API em produção**: tráfego, erros, latência p50/p95/p99, saturação (requisições em andamento e CPU), memória, tempo de inferência do YOLO e relatos.
- Prometheus: http://localhost:9090 → *Status → Targets* deve mostrar `UP`; *Alerts* mostra os 3 alertas.

| Alerta | Condição |
|---|---|
| `TaxaDeErroAlta` | mais de 5% de respostas 5xx por 1 minuto |
| `LatenciaAlta` | p95 acima de 1 s por 2 minutos |
| `ApiForaDoAr` | Prometheus sem conseguir coletar por 1 minuto |

### Disparar o alerta (para o print)
```bash
cd infra && terraform apply -var chaos_enabled=true    # liga /api/debug/erro
# GitHub → Actions → último workflow da main → Re-run all jobs (o deploy relê o Key Vault)
cd ..
docker run --rm -i -v "$PWD/observability/loadtest:/scripts" \
  -e URL=$(terraform -chdir=infra output -raw url) -e ERROS=true \
  grafana/k6 run /scripts/carga.js
```
Em uns 2 minutos o `TaxaDeErroAlta` passa de *Pending* para *Firing*. 📸 Print do Prometheus (Alerts) e do Grafana. Depois volte com `terraform apply -var chaos_enabled=false` e rode o pipeline de novo.

Para exercitar o YOLO na carga, coloque uma foto em `observability/loadtest/rua.jpg` e acrescente `-e FOTO=/scripts/rua.jpg`.

---

## Rodar localmente
```bash
cp .env.example .env
docker compose up --build
```
Acesse http://localhost:8080 (site) e http://localhost:8080/api/docs (API).

Testes da API sem Docker:
```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
```

## HTTPS
Com `habilitar_https = true` (padrão), o Caddy pede um certificado Let's Encrypt para o DNS gratuito da Azure (`alertabairro-xxxxx.<regiao>.cloudapp.azure.com`). Se a emissão falhar, use `habilitar_https = false` (só HTTP na porta 80), rode `terraform apply` e o pipeline de novo.

## Economizar crédito
```bash
az vm deallocate -g rg-alertabairro -n vm-alertabairro   # desliga (para de cobrar a VM)
az vm start      -g rg-alertabairro -n vm-alertabairro   # liga de novo
```

## Derrubar tudo no fim
```bash
cd infra && terraform destroy
```
