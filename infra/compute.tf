# A Azure exige uma chave SSH em VMs Linux. Ela é gerada aqui e nunca usada:
# a porta 22 está fechada no NSG e o login por senha está desligado.
resource "tls_private_key" "vm" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# nosemgrep: azure-instance-extensions -- o deploy usa o Run Command, que depende do agente de extensões da VM
resource "azurerm_linux_virtual_machine" "app" {
  name                            = "vm-${var.projeto}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  size                            = var.vm_size
  admin_username                  = "azureuser"
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.app.id]
  custom_data                     = base64encode(file("${path.module}/cloud-init.sh"))

  # Trusted Launch: boot seguro e TPM virtual
  secure_boot_enabled = true
  vtpm_enabled        = true

  admin_ssh_key {
    username   = "azureuser"
    public_key = tls_private_key.vm.public_key_openssh
  }

  os_disk {
    name                 = "disk-${var.projeto}-os"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS" # criptografado em repouso pela Azure (SSE)
    disk_size_gb         = var.disco_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # Identidade gerenciada: a VM lê o Key Vault e baixa do ACR sem senha nenhuma
  identity {
    type = "SystemAssigned"
  }

  boot_diagnostics {}

  tags = local.tags
}
