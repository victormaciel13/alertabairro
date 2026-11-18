variable "subscription_id" {
  description = "ID da assinatura Azure for Students (az account show --query id -o tsv)"
  type        = string
  default     = null
}

variable "localizacao" {
  description = "Região. O Azure for Students só libera algumas regiões por aluno: veja a lista no README."
  type        = string
  default     = "eastus"
}

variable "projeto" {
  description = "Prefixo dos nomes dos recursos"
  type        = string
  default     = "alertabairro"
}

variable "rm" {
  description = "RM do responsável (vai nas tags)"
  type        = string
  default     = "98384"
}

variable "vm_size" {
  description = "Tamanho da VM. Standard_B2s (2 vCPU, 4 GB) aguenta API + YOLO ONNX + Next + PostGIS."
  type        = string
  default     = "Standard_B2s"
}

variable "disco_gb" {
  description = "Tamanho do disco do sistema (GB)"
  type        = number
  default     = 32
}

variable "github_repo" {
  description = "Repositório no formato dono/repo. Se preenchido, cria a identidade OIDC do GitHub Actions (sem senha guardada no GitHub)."
  type        = string
  default     = ""
}

variable "github_oidc_prefixo" {
  description = "Prefixo do subject OIDC como o GitHub envia (ex.: repo:dono@123/repo@456). Vazio = repo:<github_repo>."
  type        = string
  default     = ""
}

variable "habilitar_https" {
  description = "true = Caddy emite certificado Let's Encrypt para o DNS da Azure (*.cloudapp.azure.com). false = só HTTP."
  type        = bool
  default     = true
}

variable "chaos_enabled" {
  description = "Liga a rota /api/debug/erro para disparar o alerta de taxa de erro na demonstração"
  type        = bool
  default     = false
}
