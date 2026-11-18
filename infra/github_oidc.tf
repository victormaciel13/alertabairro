# GitHub Actions entra na Azure por OIDC (federated credential): nenhuma senha fica no GitHub.
# Só a branch main e o ambiente "producao" deste repositório conseguem usar a identidade.
locals {
  usar_oidc = var.github_repo != ""
  # O GitHub pode mandar o "subject" no formato novo, com IDs (repo:dono@123/repo@456:...).
  # Copie o prefixo exato do log do azure/login ("subject claim") para var.github_oidc_prefixo.
  prefixo_oidc = coalesce(var.github_oidc_prefixo, "repo:${var.github_repo}")
  assuntos_oidc = {
    main     = "${local.prefixo_oidc}:ref:refs/heads/main"
    producao = "${local.prefixo_oidc}:environment:producao"
  }
}

resource "azurerm_user_assigned_identity" "github" {
  count               = local.usar_oidc ? 1 : 0
  name                = "id-${var.projeto}-github"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "github" {
  for_each            = local.usar_oidc ? local.assuntos_oidc : {}
  name                = "github-${each.key}"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.github[0].id
  issuer              = "https://token.actions.githubusercontent.com"
  audience            = ["api://AzureADTokenExchange"]
  subject             = each.value
}

# Menor privilégio: ler o grupo de recursos, enviar imagens só para este ACR e
# executar comando só nesta VM.
resource "azurerm_role_assignment" "github" {
  for_each = local.usar_oidc ? {
    leitura = { escopo = azurerm_resource_group.main.id, papel = "Reader" }
    push    = { escopo = azurerm_container_registry.main.id, papel = "AcrPush" }
    deploy  = { escopo = azurerm_linux_virtual_machine.app.id, papel = "Virtual Machine Contributor" }
  } : {}
  scope                = each.value.escopo
  role_definition_name = each.value.papel
  principal_id         = azurerm_user_assigned_identity.github[0].principal_id
}
