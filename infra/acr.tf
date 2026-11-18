resource "azurerm_container_registry" "main" {
  name                = "acr${var.projeto}${local.sufixo}" # só letras e números
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false # sem usuário/senha de admin: acesso só por identidade (RBAC)
  tags                = local.tags
}

# A VM só consegue BAIXAR imagens
resource "azurerm_role_assignment" "vm_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_virtual_machine.app.identity[0].principal_id
}
