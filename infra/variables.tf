variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "aimodelshare-playground"
}

variable "table_name" {
  type    = string
  default = "PlaygroundScores"
}

variable "enable_pitr" {
  type    = bool
  default = true
}

variable "enable_gsi_by_user" {
  type    = bool
  default = true
}

variable "safe_concurrency" {
  type    = bool
  default = false
}

variable "stage_name" {
  type    = string
  default = "prod"
}

variable "cors_allow_origins" {
  type    = list(string)
  default = ["*"]
}

variable "tags" {
  type = map(string)
  default = {
    project = "aimodelshare"
  }
}