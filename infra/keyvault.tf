# IP de quem roda o Terraform: liberado no firewall do Key Vault para gravar os segredos
data "http" "meu_ip" {
  url = "https://api.ipify.org"
}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${var.projeto}-${local.sufixo}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.atual.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = true # segredo apagado fica 7 dias recuperável (proteção contra exclusão maliciosa)
  tags                       = local.tags

  # Firewall: só a subnet da VM e o IP de quem administra
  network_acls {
    default_action             = "Deny"
    bypass                     = "AzureServices"
    virtual_network_subnet_ids = [azurerm_subnet.app.id]
    ip_rules                   = ["${chomp(data.http.meu_ip.response_body)}/32"]
  }

  # Quem roda o Terraform: gerencia os segredos
  access_policy {
    tenant_id          = data.azurerm_client_config.atual.tenant_id
    object_id          = data.azurerm_client_config.atual.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
  }

  # A VM: só LÊ os segredos
  access_policy {
    tenant_id          = data.azurerm_client_config.atual.tenant_id
    object_id          = azurerm_linux_virtual_machine.app.identity[0].principal_id
    secret_permissions = ["Get"]
  }
}

# Segredos gerados aqui: ninguém digita senha e nada vai para o Git
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "random_password" "metrics" {
  length  = 40
  special = false
}

locals {
  segredos = {
    "db-password"   = random_password.db.result
    "metrics-token" = random_password.metrics.result
    "site-address"  = var.habilitar_https ? local.dominio : ":80"
    "chaos-enabled" = tostring(var.chaos_enabled)
  }
}

# nosemgrep: azure-secret-expiration-date -- a validade está definida abaixo (a regra só reconhece data fixa em texto)
resource "azurerm_key_vault_secret" "app" {
  for_each     = local.segredos
  name         = each.key
  value        = each.value
  content_type = "text/plain"
  key_vault_id = azurerm_key_vault.main.id
  # vence em 1 ano: obriga a rotação (terraform apply -replace='random_password.db')
  expiration_date = timeadd(timestamp(), "8760h")

  lifecycle {
    ignore_changes = [expiration_date]
  }
}
