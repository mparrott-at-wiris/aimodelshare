"""
Lambda handler for aimodelshare playground API.
Supports logical tables with archive, validation, and user endpoints.
"""
import json
import os
import boto3
from decimal import Decimal
from datetime import datetime
import uuid
import re

# DynamoDB setup
TABLE_NAME = os.environ.get('TABLE_NAME', 'PlaygroundScores')
SAFE_CONCURRENCY = os.environ.get('SAFE_CONCURRENCY', 'false').lower() == 'true'

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def validate_table_id(table_id):
    """Validate table ID format"""
    if not table_id or not isinstance(table_id, str):
        return False
    # Allow alphanumeric, underscores, hyphens, up to 64 chars
    return bool(re.match(r'^[a-zA-Z0-9_-]{1,64}$', table_id))

def validate_username(username):
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False
    # Allow alphanumeric, underscores, hyphens, up to 64 chars
    return bool(re.match(r'^[a-zA-Z0-9_-]{1,64}$', username))

def create_response(status_code, body, headers=None):
    """Create standardized API response"""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,PUT,PATCH,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, default=decimal_default)
    }

def create_table(event):
    """Create a new logical table entry"""
    try:
        body = json.loads(event.get('body', '{}'))
        table_id = body.get('tableId')
        display_name = body.get('displayName', table_id)
        
        if not validate_table_id(table_id):
            return create_response(400, {
                'error': 'Invalid tableId. Must be alphanumeric with underscores/hyphens, max 64 chars'
            })
        
        # Check if table already exists
        try:
            response = table.get_item(
                Key={'tableId': table_id, 'username': '_metadata'}
            )
            if 'Item' in response:
                return create_response(409, {
                    'error': f'Table {table_id} already exists'
                })
        except Exception:
            pass
        
        metadata = {
            'tableId': table_id,
            'username': '_metadata',
            'displayName': display_name,
            'createdAt': datetime.utcnow().isoformat(),
            'isArchived': False,
            'userCount': 0
        }
        
        table.put_item(Item=metadata)
        
        return create_response(201, {
            'tableId': table_id,
            'displayName': display_name,
            'message': 'Table created successfully'
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def list_tables(event):
    """List all logical tables"""
    try:
        response = table.query(
            IndexName='byUser',
            KeyConditionExpression='username = :username',
            ExpressionAttributeValues={':username': '_metadata'}
        )
        
        tables = []
        for item in response.get('Items', []):
            tables.append({
                'tableId': item['tableId'],
                'displayName': item.get('displayName', item['tableId']),
                'createdAt': item.get('createdAt'),
                'isArchived': item.get('isArchived', False),
                'userCount': item.get('userCount', 0)
            })
        
        tables.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        return create_response(200, {'tables': tables})
        
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def get_table(event):
    """Get specific table metadata"""
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        
        response = table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'}
        )
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Table not found'})
        
        item = response['Item']
        return create_response(200, {
            'tableId': item['tableId'],
            'displayName': item.get('displayName', item['tableId']),
            'createdAt': item.get('createdAt'),
            'isArchived': item.get('isArchived', False),
            'userCount': item.get('userCount', 0)
        })
        
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def patch_table(event):
    """Update table metadata (e.g., archive/unarchive)"""
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        body = json.loads(event.get('body', '{}'))
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        
        response = table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'}
        )
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Table not found'})
        
        update_expression = []
        expression_values = {}
        
        if 'displayName' in body:
            update_expression.append('displayName = :display_name')
            expression_values[':display_name'] = body['displayName']
        
        if 'isArchived' in body:
            update_expression.append('isArchived = :is_archived')
            expression_values[':is_archived'] = bool(body['isArchived'])
        
        if not update_expression:
            return create_response(400, {'error': 'No valid fields to update'})
        
        update_expression.append('updatedAt = :updated_at')
        expression_values[':updated_at'] = datetime.utcnow().isoformat()
        
        table.update_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            UpdateExpression='SET ' + ', '.join(update_expression),
            ExpressionAttributeValues=expression_values
        )
        
        return create_response(200, {'message': 'Table updated successfully'})
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def list_users(event):
    """List all users for a specific table"""
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        
        metadata_response = table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'}
        )
        
        if 'Item' not in metadata_response:
            return create_response(404, {'error': 'Table not found'})
        
        response = table.query(
            KeyConditionExpression='tableId = :table_id',
            FilterExpression='username <> :metadata',
            ExpressionAttributeValues={':table_id': table_id, ':metadata': '_metadata'}
        )
        
        users = []
        for item in response.get('Items', []):
            users.append({
                'username': item['username'],
                'submissionCount': item.get('submissionCount', 0),
                'totalCount': item.get('totalCount', 0),
                'lastUpdated': item.get('lastUpdated')
            })
        
        users.sort(key=lambda x: x.get('submissionCount', 0), reverse=True)
        
        return create_response(200, {'users': users})
        
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def get_user(event):
    """Get specific user data for a table"""
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        username = params.get('username')
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        if not validate_username(username):
            return create_response(400, {'error': 'Invalid username format'})
        
        metadata_response = table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'}
        )
        if 'Item' not in metadata_response:
            return create_response(404, {'error': 'Table not found'})
        
        response = table.get_item(
            Key={'tableId': table_id, 'username': username}
        )
        if 'Item' not in response:
            return create_response(404, {'error': 'User not found in table'})
        
        item = response['Item']
        return create_response(200, {
            'username': item['username'],
            'submissionCount': item.get('submissionCount', 0),
            'totalCount': item.get('totalCount', 0),
            'lastUpdated': item.get('lastUpdated')
        })
        
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def put_user(event):
    """Update or create user data for a table"""
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        username = params.get('username')
        body = json.loads(event.get('body', '{}'))
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        if not validate_username(username):
            return create_response(400, {'error': 'Invalid username format'})
        
        metadata_response = table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'}
        )
        if 'Item' not in metadata_response:
            return create_response(404, {'error': 'Table not found'})
        
        submission_count = body.get('submissionCount')
        total_count = body.get('totalCount')
        
        if submission_count is None or total_count is None:
            return create_response(400, {
                'error': 'submissionCount and totalCount are required'
            })
        try:
            submission_count = int(submission_count)
            total_count = int(total_count)
        except (ValueError, TypeError):
            return create_response(400, {
                'error': 'submissionCount and totalCount must be integers'
            })
        if submission_count < 0 or total_count < 0:
            return create_response(400, {
                'error': 'submissionCount and totalCount must be non-negative'
            })
        
        existing_response = table.get_item(
            Key={'tableId': table_id, 'username': username}
        )
        user_exists = 'Item' in existing_response
        
        user_data = {
            'tableId': table_id,
            'username': username,
            'submissionCount': submission_count,
            'totalCount': total_count,
            'lastUpdated': datetime.utcnow().isoformat()
        }
        table.put_item(Item=user_data)
        
        if not user_exists:
            table.update_item(
                Key={'tableId': table_id, 'username': '_metadata'},
                UpdateExpression='ADD userCount :inc',
                ExpressionAttributeValues={':inc': 1}
            )
        
        return create_response(200, {
            'username': username,
            'submissionCount': submission_count,
            'totalCount': total_count,
            'message': 'User data updated successfully'
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def handler(event, context):
    """Main Lambda handler with robust HTTP API v2 routing."""
    try:
        # Fast-path for CORS preflight
        method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        if method == 'OPTIONS':
            return create_response(200, {})
        
        route_key = event.get('routeKey')  # e.g. "GET /tables"
        
        # Dispatch based on routeKey (preferred for HTTP API v2)
        if route_key == 'POST /tables':
            return create_table(event)
        elif route_key == 'GET /tables':
            return list_tables(event)
        elif route_key == 'GET /tables/{tableId}':
            return get_table(event)
        elif route_key == 'PATCH /tables/{tableId}':
            return patch_table(event)
        elif route_key == 'GET /tables/{tableId}/users':
            return list_users(event)
        elif route_key == 'GET /tables/{tableId}/users/{username}':
            return get_user(event)
        elif route_key == 'PUT /tables/{tableId}/users/{username}':
            return put_user(event)
        else:
            # Fallback: previous path-based routing (only if routeKey missing)
            path = event.get('rawPath') or event.get('path') or ''
            stage = event.get('requestContext', {}).get('stage')
            if stage and path.startswith(f'/{stage}/'):
                path = path[len(stage) + 1:]  # strip /{stage}
            
            if method == 'POST' and path == '/tables':
                return create_table(event)
            elif method == 'GET' and path == '/tables':
                return list_tables(event)
            elif method == 'GET' and path.startswith('/tables/') and path.count('/') == 2:
                return get_table(event)
            elif method == 'PATCH' and path.startswith('/tables/') and path.count('/') == 2:
                return patch_table(event)
            elif method == 'GET' and path.endswith('/users') and path.count('/') == 3:
                return list_users(event)
            elif method == 'GET' and '/users/' in path and path.count('/') == 4:
                return get_user(event)
            elif method == 'PUT' and '/users/' in path and path.count('/') == 4:
                return put_user(event)
            else:
                return create_response(404, {'error': 'Route not found'})
            
    except Exception as e:
        return create_response(500, {'error': f'Unexpected error: {str(e)}'})
            
    except Exception as e:
        return create_response(500, {'error': f'Unexpected error: {str(e)}'})
