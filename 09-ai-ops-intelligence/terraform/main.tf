terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# Random suffix so resource names are globally unique
# (Azure requires some names to be unique across all customers worldwide)
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  # Shorthand used to name everything consistently
  prefix = "${var.project_name}-${var.environment}-${random_string.suffix.result}"

  # Tags applied to every resource — helps with cost tracking and auditing
  tags = {
    project     = "09-ai-ops-intelligence"
    environment = var.environment
    owner       = "MEEK"
    managed_by  = "terraform"
  }
}

# The resource group is like a folder in Azure that holds all your project resources
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.prefix}"
  location = var.location
  tags     = local.tags
}
