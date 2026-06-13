# Project 14: Inventory Watchdog
# Input variables

variable "location" {
  description = "Azure region for all resources. eastus2 chosen for GPT-4o availability."
  type        = string
  default     = "eastus2"
}

variable "project" {
  description = "Project tag applied to all resources"
  type        = string
  default     = "14-inventory-watchdog"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}
