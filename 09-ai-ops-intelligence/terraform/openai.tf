# ─────────────────────────────────────────────
# AZURE OPENAI
# This is the AI brain of the project. It reads
# flagged alerts from Stream Analytics and writes
# plain English explanations of what is wrong,
# how urgent it is, and what to do about it.
# It also generates the weekly DR health report.
# ─────────────────────────────────────────────
resource "azurerm_cognitive_account" "openai" {
  name                  = "oai-${local.prefix}"
  location              = "eastus"  # OpenAI is not available in eastus2 yet
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.prefix}"
  tags                  = local.tags
}

# The actual AI model deployment
# GPT-4o-mini is fast, cheap, and more than capable
# for alert classification and report writing
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = var.openai_model
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }

  scale {
    type     = "Standard"
    capacity = 10  # 10,000 tokens per minute — plenty for dev
  }
}

# Store the OpenAI endpoint and key in Key Vault
# so scripts never have secrets hardcoded in code
resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = azurerm_cognitive_account.openai.name
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}
