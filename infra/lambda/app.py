"""
Lambda handler for aimodelshare playground API.
(Definitive Fix: Corrected list_tables to scan the entire table if needed, ensuring filtered items are always found.)
"""
import json
import os
import boto3
from decimal import Decimal
from datetime import datetime
import re
import time
import random
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# DynamoDB setup
TABLE_NAME = os.environ.get('TABLE_NAME', 'PlaygroundScores')
SAFE_CONCURRENCY = os.environ.get('SAFE_CONCURRENCY', 'false').lower() == 'true'
READ_CONSISTENT = os.environ.get('READ_CONSISTENT', 'true').lower() == 'true'

DEFAULT_PAGE_LIMIT = int(os.environ.get('DEFAULT_PAGE_LIMIT', '50'))
MAX_PAGE_LIMIT = int(os.environ.get('MAX_PAGE_LIMIT', '500'))

dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
table = dynamodb.Table(TABLE_NAME)

print(f"[BOOT] Using DynamoDB table: {TABLE_NAME} | SAFE_CONCURRENCY={SAFE_CONCURRENCY} | READ_CONSISTENT={READ_CONSISTENT}")

_TABLE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        f = float(obj)
        if f.is_integer():
            return int(f)
        return f
    raise TypeError

def validate_table_id(table_id):
    return bool(table_id and isinstance(table_id, str) and _TABLE_ID_RE.match(table_id))

def validate_username(username):
    return bool(username and isinstance(username, str) and _USERNAME_RE.match(username))

def create_response(status_code, body, headers=None):
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

RETRYABLE_ERRORS = {
    'ProvisionedThroughputExceededException',
    'ThrottlingException',
    'InternalServerError',
    'TransactionCanceledException'
}

def retry_dynamo(op_fn, max_attempts=5, base_delay=0.05, context=None):
    attempt = 0
    while True:
        try:
            return op_fn()
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code')
            if code in RETRYABLE_ERRORS and attempt < max_attempts - 1:
                remaining_ms = context.get_remaining_time_in_millis() if context else 10_000
                if remaining_ms < 500:
                    raise
                sleep_time = (base_delay * (2 ** attempt)) * (1 + random.random() * 0.5)
                sleep_time = min(sleep_time, 0.8)
                print(f"[RETRY] DynamoDB error {code}, attempt {attempt+1}/{max_attempts}, sleeping {sleep_time:.3f}s")
                time.sleep(sleep_time)
                attempt += 1
                continue
            raise
        except Exception:
            raise

def parse_pagination_params(event):
    qs = event.get('queryStringParameters') or {}
    try:
        limit = int(qs.get('limit', DEFAULT_PAGE_LIMIT))
    except ValueError:
        limit = DEFAULT_PAGE_LIMIT
    limit = max(1, min(limit, MAX_PAGE_LIMIT))
    last_key_raw = qs.get('lastKey')
    exclusive_start_key = None
    if last_key_raw:
        try:
            exclusive_start_key = json.loads(last_key_raw)
        except Exception:
            print('[WARN] Malformed lastKey ignored.')
    return limit, exclusive_start_key

def build_paged_body(items_key, items, last_evaluated_key):
    body = {items_key: items}
    if last_evaluated_key:
        body['lastKey'] = last_evaluated_key
    return body

def create_table(event):
    try:
        body = json.loads(event.get('body', '{}'))
        table_id = body.get('tableId')
        display_name = body.get('displayName', table_id)
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId. Must be alphanumeric with underscores/hyphens, max 64 chars'})
        try:
            resp = retry_dynamo(lambda: table.get_item(
                Key={'tableId': table_id, 'username': '_metadata'},
                ConsistentRead=READ_CONSISTENT
            ))
            if 'Item' in resp:
                return create_response(409, {'error': f'Table {table_id} already exists'})
        except ClientError as e:
            print(f"[WARN] get_item metadata error during create_table: {e}")
        metadata = {
            'tableId': table_id,
            'username': '_metadata',
            'displayName': display_name,
            'createdAt': datetime.utcnow().isoformat(),
            'isArchived': False,
            'userCount': 0
        }
        retry_dynamo(lambda: table.put_item(Item=metadata))
        return create_response(201, {'tableId': table_id, 'displayName': display_name, 'message': 'Table created successfully'})
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"[ERROR] create_table exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def list_tables(event):
    """
    Paginated list of tables using a STRONGLY CONSISTENT Scan.
    This implementation correctly handles pagination for a filtered scan by scanning
    the entire table to collect all metadata items before paginating the results.
    """
    try:
        limit, exclusive_start_key = parse_pagination_params(event)
        
        scan_kwargs = {
            'FilterExpression': Attr('username').eq('_metadata'),
            'ConsistentRead': True
        }
        
        all_metadata_items = []
        last_key_from_ddb = None
        
        # Loop to scan the entire table and collect all items matching the filter
        while True:
            if last_key_from_ddb:
                scan_kwargs['ExclusiveStartKey'] = last_key_from_ddb
            
            resp = retry_dynamo(lambda: table.scan(**scan_kwargs))
            
            all_metadata_items.extend(resp.get('Items', []))
            
            last_key_from_ddb = resp.get('LastEvaluatedKey')
            if not last_key_from_ddb:
                break # Scanned the entire table

        # Now, paginate the collected results manually
        all_metadata_items.sort(key=lambda x: (x.get('createdAt') or ''), reverse=True)
        
        start_index = 0
        if exclusive_start_key:
            # Find the index of the item represented by the start key
            start_table_id = exclusive_start_key.get('tableId')
            try:
                start_index = next(i for i, item in enumerate(all_metadata_items) if item.get('tableId') == start_table_id) + 1
            except StopIteration:
                start_index = 0 # Key not found, start from beginning

        end_index = start_index + limit
        page_items = all_metadata_items[start_index:end_index]
        
        response_last_key = None
        if end_index < len(all_metadata_items):
            last_item_on_page = page_items[-1]
            response_last_key = {
                'tableId': last_item_on_page['tableId'],
                'username': last_item_on_page['username']
            }

        tables = [{
            'tableId': item['tableId'],
            'displayName': item.get('displayName', item['tableId']),
            'createdAt': item.get('createdAt'),
            'isArchived': item.get('isArchived', False),
            'userCount': item.get('userCount', 0)
        } for item in page_items]
        
        return create_response(200, build_paged_body('tables', tables, response_last_key))
    except Exception as e:
        print(f"[ERROR] list_tables exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def get_table(event):
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        resp = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in resp:
            return create_response(404, {'error': 'Table not found'})
        item = resp['Item']
        return create_response(200, {
            'tableId': item['tableId'],
            'displayName': item.get('displayName', item['tableId']),
            'createdAt': item.get('createdAt'),
            'isArchived': item.get('isArchived', False),
            'userCount': item.get('userCount', 0)
        })
    except Exception as e:
        print(f"[ERROR] get_table exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def patch_table(event):
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        body = json.loads(event.get('body', '{}'))
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        resp = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in resp:
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
        retry_dynamo(lambda: table.update_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            UpdateExpression='SET ' + ', '.join(update_expression),
            ExpressionAttributeValues=expression_values
        ))
        return create_response(200, {'message': 'Table updated successfully'})
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"[ERROR] patch_table exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def list_users(event):
    """Paginated list of users with correct pagination logic."""
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        meta = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in meta:
            return create_response(404, {'error': 'Table not found'})

        limit, exclusive_start_key = parse_pagination_params(event)
        
        query_kwargs = {
            'KeyConditionExpression': Key('tableId').eq(table_id),
            'Limit': limit + 2, 
            'ConsistentRead': READ_CONSISTENT
        }
        if exclusive_start_key:
            query_kwargs['ExclusiveStartKey'] = exclusive_start_key

        resp = retry_dynamo(lambda: table.query(**query_kwargs))
        
        all_items = resp.get('Items', [])
        
        user_items = [item for item in all_items if item.get('username') != '_metadata']
        
        has_next_page = len(user_items) > limit
        page_items = user_items[:limit]
        
        response_last_key = None
        if has_next_page:
            last_item_on_page = page_items[-1]
            response_last_key = {
                'tableId': last_item_on_page['tableId'],
                'username': last_item_on_page['username']
            }

        users_to_return = [{
            'username': item['username'],
            'submissionCount': item.get('submissionCount', 0),
            'totalCount': item.get('totalCount', 0),
            'lastUpdated': item.get('lastUpdated')
        } for item in page_items]
        
        users_to_return.sort(key=lambda x: x.get('submissionCount', 0), reverse=True)
        
        return create_response(200, build_paged_body('users', users_to_return, response_last_key))
    except Exception as e:
        print(f"[ERROR] list_users exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def get_user(event):
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        username = params.get('username')
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        if not validate_username(username):
            return create_response(400, {'error': 'Invalid username format'})
        meta = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in meta:
            return create_response(404, {'error': 'Table not found'})
        resp = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': username},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in resp:
            return create_response(404, {'error': 'User not found in table'})
        item = resp['Item']
        return create_response(200, {
            'username': item['username'],
            'submissionCount': item.get('submissionCount', 0),
            'totalCount': item.get('totalCount', 0),
            'lastUpdated': item.get('lastUpdated')
        })
    except Exception as e:
        print(f"[ERROR] get_user exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def put_user(event):
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        username = params.get('username')
        body = json.loads(event.get('body', '{}'))
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        if not validate_username(username):
            return create_response(400, {'error': 'Invalid username format'})
        meta = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in meta:
            return create_response(404, {'error': 'Table not found'})
        submission_count = body.get('submissionCount')
        total_count = body.get('totalCount')
        if submission_count is None or total_count is None:
            return create_response(400, {'error': 'submissionCount and totalCount are required'})
        try:
            submission_count = int(submission_count)
            total_count = int(total_count)
        except (ValueError, TypeError):
            return create_response(400, {'error': 'submissionCount and totalCount must be integers'})
        if submission_count < 0 or total_count < 0:
            return create_response(400, {'error': 'submissionCount and totalCount must be non-negative'})
        user_data = {
            'tableId': table_id,
            'username': username,
            'submissionCount': submission_count,
            'totalCount': total_count,
            'lastUpdated': datetime.utcnow().isoformat()
        }
        created_new = False
        try:
            retry_dynamo(lambda: table.put_item(
                Item=user_data,
                ConditionExpression="attribute_not_exists(username)"
            ))
            created_new = True
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code')
            if code == 'ConditionalCheckFailedException':
                retry_dynamo(lambda: table.put_item(Item=user_data))
            else:
                print(f"[ERROR] put_user unexpected ClientError {code}: {e}")
                return create_response(500, {'error': f'Internal server error: {code}'})
        except Exception as e:
            print(f"[ERROR] put_user unexpected exception: {e}")
            return create_response(500, {'error': f'Internal server error: {str(e)}'})
        if created_new:
            try:
                retry_dynamo(lambda: table.update_item(
                    Key={'tableId': table_id, 'username': '_metadata'},
                    UpdateExpression='ADD userCount :inc',
                    ExpressionAttributeValues={':inc': 1}
                ))
            except Exception as e:
                print(f"[WARN] Failed to increment userCount for new user {username}: {e}")
        return create_response(200, {
            'username': username,
            'submissionCount': submission_count,
            'totalCount': total_count,
            'message': 'User data updated successfully',
            'createdNew': created_new
        })
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"[ERROR] put_user outer exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def health(event):
    status = {
        'tableName': TABLE_NAME,
        'gsiByUserActive': False,
        'timestamp': datetime.utcnow().isoformat()
    }
    try:
        desc = dynamodb_client.describe_table(TableName=TABLE_NAME)
        gsis = desc.get('Table', {}).get('GlobalSecondaryIndexes', []) or []
        for g in gsis:
            if g.get('IndexName') == 'byUser' and g.get('IndexStatus') == 'ACTIVE':
                status['gsiByUserActive'] = True
                break
    except Exception as e:
        status['error'] = str(e)
    return create_response(200, status)

def handler(event, context):
    try:
        method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        if method == 'OPTIONS':
            return create_response(200, {})
        route_key = event.get('routeKey')
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
        elif route_key == 'GET /health':
            return health(event)

        path = event.get('rawPath') or event.get('path') or ''
        stage = event.get('requestContext', {}).get('stage')
        if stage and path.startswith(f'/{stage}/'):
            path = path[len(stage) + 1:]

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
        elif method == 'GET' and path == '/health':
            return health(event)

        return create_response(404, {'error': 'Route not found'})
    except Exception as e:
        print(f"[ERROR] handler unexpected exception: {e}")
        return create_response(500, {'error': f'Unexpected error: {str(e)}'})
