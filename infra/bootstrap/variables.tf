variable "region" {
  description = "AWS region for the Terraform state resources"
  type        = string
  default     = "us-east-1"
}

variable "github_repository" {
  description = "GitHub repository in the format 'owner/repo'"
  type        = string
  default     = "mparrott-at-wiris/aimodelshare"
}

variable "github_oidc_thumbprint" {
  description = "GitHub OIDC thumbprint for the identity provider"
  type        = string
  default     = "6938fd4d98bab03faadb97b34396831e3780aea1"  # GitHub's current thumbprint
}