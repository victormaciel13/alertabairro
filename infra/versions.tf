terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.20, < 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }

  # Estado local (terraform.tfstate fica fora do Git, ver .gitignore).
  # Para trabalhar em grupo, troque por um backend "azurerm" num Storage Account.
}

provider "azurerm" {
  # vazio = usa a assinatura do "az login" (ou a variável ARM_SUBSCRIPTION_ID)
  subscription_id = var.subscription_id

  resource_provider_registrations = "none"
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false # com purge protection o Key Vault fica 7 dias na lixeira
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}
