output "api_base_url" {
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/${aws_apigatewayv2_stage.stage.name}"
  description = "Base URL for API"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.playground.name
  description = "DDB table"
}

output "lambda_name" {
  value       = aws_lambda_function.api.function_name
  description = "Lambda name"
}