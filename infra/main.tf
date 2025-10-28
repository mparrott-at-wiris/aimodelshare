terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }

  # Remote state backend (created by bootstrap)
  backend "s3" {
    bucket         = "aimodelshare-tfstate-prod-copilot-2024"
    key            = "aimodelshare/infra/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "aimodelshare-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}

locals {
  workspace   = terraform.workspace
  name_prefix = "${var.name_prefix}-${local.workspace}"
  stage_name  = local.workspace == "default" ? var.stage_name : local.workspace
  table_name  = "${var.table_name}-${local.workspace}"
  tags = merge(var.tags, {
    workspace = local.workspace
  })
}

resource "null_resource" "state_seed" {
  triggers = {
    workspace = local.workspace
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_dynamodb_table" "playground" {
  name         = local.table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "tableId"
  range_key = "username"

  attribute {
    name = "tableId"
    type = "S"
  }
  attribute {
    name = "username"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  dynamic "global_secondary_index" {
    for_each = var.enable_gsi_by_user ? [1] : []
    content {
      name            = "byUser"
      hash_key        = "username"
      range_key       = "tableId"
      projection_type = "ALL"
    }
  }

  # Optional leaderboard GSI for list_users descending submissionCount ordering
  # Note: DynamoDB does not support descending sort order natively on range keys
  # This GSI would require application-level workarounds (e.g., storing negative values)
  # For now, keeping in-memory sorting as the recommended approach
  # dynamic "global_secondary_index" {
  #   for_each = var.enable_gsi_leaderboard ? [1] : []
  #   content {
  #     name            = "byTableSubmission"
  #     hash_key        = "tableId"
  #     range_key       = "submissionCount"
  #     projection_type = "ALL"
  #   }
  # }

  # Uncomment if enabling leaderboard GSI:
  # attribute {
  #   name = "submissionCount"
  #   type = "N"
  # }

  tags = local.tags
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda.zip"
}

variable "use_layer" {
  type    = bool
  default = false
}

variable "layer_zip_path" {
  type    = string
  default = "./layer/layer.zip"
}

resource "aws_lambda_layer_version" "extra" {
  count               = var.use_layer ? 1 : 0
  filename            = var.layer_zip_path
  layer_name          = "${local.name_prefix}-extra"
  compatible_runtimes = ["python3.11"]
  description         = "Extra Python deps (e.g., aimodelshare)"
}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "ddb_rw" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:DescribeTable",
      "dynamodb:Scan"
    ]
    resources = [
      aws_dynamodb_table.playground.arn,
      "${aws_dynamodb_table.playground.arn}/index/*"
    ]
  }
}

resource "aws_iam_policy" "ddb_rw" {
  name        = "${local.name_prefix}-ddb-rw"
  description = "Allow Lambda read/write on the Playground table"
  policy      = data.aws_iam_policy_document.ddb_rw.json
}

resource "aws_iam_role_policy_attachment" "attach_ddb_rw" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.ddb_rw.arn
}


resource "aws_lambda_function" "api" {
  function_name    = "${local.name_prefix}-api"
  role             = aws_iam_role.lambda_exec_role.arn
  runtime          = "python3.11"
  handler          = "app.handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout     = 10
  memory_size = 256

  environment {
    variables = {
      TABLE_NAME                        = aws_dynamodb_table.playground.name
      SAFE_CONCURRENCY                  = var.safe_concurrency ? "true" : "false"
      DEFAULT_PAGE_LIMIT                = "50"
      MAX_PAGE_LIMIT                    = "500"
      USE_METADATA_GSI                  = var.use_metadata_gsi ? "true" : "false"
      READ_CONSISTENT                   = var.read_consistent ? "true" : "false"
      DEFAULT_TABLE_PAGE_LIMIT          = tostring(var.default_table_page_limit)
      USE_LEADERBOARD_GSI               = var.use_leaderboard_gsi ? "true" : "false"
      AUTH_ENABLED                      = var.auth_enabled ? "true" : "false"
      MC_ENFORCE_NAMING                 = var.mc_enforce_naming ? "true" : "false"
      MORAL_COMPASS_ALLOWED_SUFFIXES    = var.moral_compass_allowed_suffixes
      ALLOW_TABLE_DELETE                = var.allow_table_delete ? "true" : "false"
      ALLOW_PUBLIC_READ                 = var.allow_public_read ? "true" : "false"
      AWS_REGION_NAME                   = var.region
    }
  }

  layers = var.use_layer ? [aws_lambda_layer_version.extra[0].arn] : []
  tags   = local.tags
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.name_prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = ["GET", "PUT", "PATCH", "POST", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }

  tags = local.tags
}

resource "aws_apigatewayv2_integration" "lambda_proxy" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.api.invoke_arn
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "route_create_table" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /tables"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_list_tables" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /tables"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_get_table" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /tables/{tableId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_patch_table" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PATCH /tables/{tableId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_delete_table" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "DELETE /tables/{tableId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_list_users" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /tables/{tableId}/users"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_get_user" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /tables/{tableId}/users/{username}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}
resource "aws_apigatewayv2_route" "route_put_user" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PUT /tables/{tableId}/users/{username}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

# Moral compass routes
resource "aws_apigatewayv2_route" "route_put_moral_compass" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PUT /tables/{tableId}/users/{username}/moral-compass"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

# Legacy moral compass route (backward compatibility)
resource "aws_apigatewayv2_route" "route_put_moral_compass_legacy" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PUT /tables/{tableId}/users/{username}/moralcompass"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

# New health route
resource "aws_apigatewayv2_route" "route_health" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

resource "aws_apigatewayv2_stage" "stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = local.stage_name
  auto_deploy = true
  tags        = local.tags
}

resource "aws_lambda_permission" "allow_invoke" {
  statement_id  = "AllowInvokeFromHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

