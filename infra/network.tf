resource "azurerm_virtual_network" "main" {
  name                = "vnet-${var.projeto}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = ["10.20.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "app" {
  name                            = "snet-app"
  resource_group_name             = azurerm_resource_group.main.name
  virtual_network_name            = azurerm_virtual_network.main.name
  address_prefixes                = ["10.20.1.0/24"]
  service_endpoints               = ["Microsoft.KeyVault"] # a VM fala com o Key Vault pela rede da Azure
  default_outbound_access_enabled = false                  # a saída é só pelo IP público da VM
}

# ------------------------------------------------------------------ NSG (firewall)
# Entrada: só 80 e 443. NÃO existe regra para a porta 22: sem SSH.
# A administração é pelo "Executar comando" (Run Command) da Azure, que exige login no Entra ID.
resource "azurerm_network_security_group" "app" {
  name                = "nsg-${var.projeto}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags

  security_rule {
    name                    = "permitir-http-https"
    description             = "Site publico do AlertaBairro"
    priority                = 100
    direction               = "Inbound"
    access                  = "Allow"
    protocol                = "Tcp"
    source_port_range       = "*"
    destination_port_ranges = ["80", "443"]
    # trivy:ignore:AVD-AZU-0047 site público: 80/443 precisam aceitar qualquer IP (a porta 22 continua fechada)
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "negar-todo-o-resto"
    description                = "Bloqueia qualquer outra entrada vinda da internet (inclusive SSH 22 e RDP 3389)"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

# IP fixo com DNS gratuito da Azure: alertabairro-xxxxx.<regiao>.cloudapp.azure.com
resource "azurerm_public_ip" "app" {
  name                = "pip-${var.projeto}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = "${var.projeto}-${local.sufixo}"
  tags                = local.tags
}

resource "azurerm_network_interface" "app" {
  name                = "nic-${var.projeto}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags

  ip_configuration {
    name                          = "principal"
    subnet_id                     = azurerm_subnet.app.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.app.id
  }
}

# O mesmo NSG também na placa de rede (defesa em profundidade)
resource "azurerm_network_interface_security_group_association" "app" {
  network_interface_id      = azurerm_network_interface.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}
