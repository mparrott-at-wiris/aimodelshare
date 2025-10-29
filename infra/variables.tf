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

variable "use_metadata_gsi" {
  type        = bool
  default     = false
  description = "Enable GSI-based query for list_tables (USE_METADATA_GSI)"
}

variable "read_consistent" {
  type        = bool
  default     = true
  description = "Enable strongly consistent reads for list endpoints (READ_CONSISTENT)"
}

variable "default_table_page_limit" {
  type        = number
  default     = 50
  description = "Default page limit for list_tables endpoint"
}

variable "enable_gsi_leaderboard" {
  type        = bool
  default     = false
  description = "Enable leaderboard GSI (byTableSubmission) for list_users ordering"
}

variable "use_leaderboard_gsi" {
  type        = bool
  default     = false
  description = "Enable leaderboard GSI query path in list_users (USE_LEADERBOARD_GSI)"
}

variable "auth_enabled" {
  type        = bool
  default     = true
  description = "Enable authentication and authorization checks"
}

variable "mc_enforce_naming" {
  type        = bool
  default     = false
  description = "Enforce moral compass table naming convention (<playgroundId>-mc)"
}

variable "moral_compass_allowed_suffixes" {
  type        = string
  default     = "-mc"
  description = "Comma-separated list of allowed suffixes for moral compass tables"
}

variable "allow_table_delete" {
  type        = bool
  default     = false
  description = "Allow table deletion via DELETE /tables/{tableId} endpoint"
}

variable "allow_public_read" {
  type        = bool
  default     = true
  description = "Allow public read access to tables and users when auth is enabled"
}
