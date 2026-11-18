output "url" {
  description = "Endereço público do AlertaBairro (vai na variável APP_URL do GitHub)"
  value       = local.url
}

output "ip_publico" {
  value = azurerm_public_ip.app.ip_address
}

output "github_variaveis" {
  description = "Copie cada par para Settings > Secrets and variables > Actions > Variables"
  value = {
    AZURE_CLIENT_ID       = one(azurerm_user_assigned_identity.github[*].client_id)
    AZURE_TENANT_ID       = data.azurerm_client_config.atual.tenant_id
    AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.atual.subscription_id
    RESOURCE_GROUP        = azurerm_resource_group.main.name
    VM_NAME               = azurerm_linux_virtual_machine.app.name
    ACR_NAME              = azurerm_container_registry.main.name
    KEY_VAULT             = azurerm_key_vault.main.name
    APP_URL               = local.url
  }
}

output "metrics_target" {
  description = "Alvo para o Prometheus local"
  value       = var.habilitar_https ? "${local.dominio}:443" : "${azurerm_public_ip.app.ip_address}:80"
}

output "comando_token_metricas" {
  description = "Rode este comando para pegar o token do /metrics (não fica exposto no output)"
  value       = "az keyvault secret show --vault-name ${azurerm_key_vault.main.name} --name metrics-token --query value -o tsv"
}
