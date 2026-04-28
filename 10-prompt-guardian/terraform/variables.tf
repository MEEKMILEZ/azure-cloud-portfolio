variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "openai_location" {
  description = "Azure region for OpenAI — must support GPT-4o"
  type        = string
  default     = "eastus"
}

variable "notification_email" {
  description = "Email address for override notifications"
  type        = string
  default     = "paschalnnenna@hotmail.com"
}
