variable "location" {
  description = "Azure region where all resources will be created"
  type        = string
  default     = "eastus2"
}

variable "project_name" {
  description = "Short name used to label all resources"
  type        = string
  default     = "aiops"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "notification_email" {
  description = "Email address that receives critical alerts and DR reports"
  type        = string
}

variable "openai_model" {
  description = "Azure OpenAI model to use for alert triage and DR report generation"
  type        = string
  default     = "gpt-4o-mini"
}

variable "rto_target_minutes" {
  description = "Recovery Time Objective — how many minutes your DR plan promises systems will be back online"
  type        = number
  default     = 30
}

variable "rpo_target_minutes" {
  description = "Recovery Point Objective — how many minutes of data loss is acceptable during a disaster"
  type        = number
  default     = 15
}
