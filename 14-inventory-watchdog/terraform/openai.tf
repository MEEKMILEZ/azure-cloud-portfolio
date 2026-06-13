# Project 14: Inventory Watchdog
# Narration layer. The model turns computed findings into a readable
# weekly digest. The custom subdomain is required so the Function
# can authenticate with its managed identity instead of an API key.
#
# Model choice note: the gpt-4o family entered its deprecation window
# ahead of an October 2026 retirement, and Azure blocks new deployments
# of deprecating models. gpt-5-mini retires February 2027, costs less,
# and summarization is well within its strengths.
#
# Provider note: azurerm 3.x calls the deployment sizing block "scale".
# It was renamed to "sku" in provider 4.x.

resource "azurerm_cognitive_account" "openai" {
  name                  = "oai-invwatch-${local.suffix}"
  resource_group_name   = azurerm_resource_group.main.name
  location              = azurerm_resource_group.main.location
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-invwatch-${local.suffix}"
  tags                  = local.tags
}

resource "azurerm_cognitive_deployment" "narrator" {
  name                 = "gpt-5-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-5-mini"
    version = "2025-08-07"
  }

  scale {
    type     = "GlobalStandard"
    capacity = 10
  }
}
