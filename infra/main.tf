# Sufixo aleatório: ACR, Key Vault e DNS precisam de nome único no mundo todo
resource "random_string" "sufixo" {
  length  = 5
  upper   = false
  special = false
}

locals {
  sufixo = random_string.sufixo.result
  tags = {
    Projeto       = "AlertaBairro"
    Disciplina    = "Secure DevOps & Cloud"
    Responsavel   = "RM${var.rm}"
    GerenciadoPor = "Terraform"
  }
  dominio = azurerm_public_ip.app.fqdn
  url     = var.habilitar_https ? "https://${local.dominio}" : "http://${azurerm_public_ip.app.ip_address}"
}

data "azurerm_client_config" "atual" {}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.projeto}"
  location = var.localizacao
  tags     = local.tags
}
