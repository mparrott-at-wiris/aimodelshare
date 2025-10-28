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
from urllib.parse import urlparse

# DynamoDB setup
TABLE_NAME = os.environ.get('TABLE_NAME', 'PlaygroundScores')
SAFE_CONCURRENCY = os.environ.get('SAFE_CONCURRENCY', 'false').lower() == 'true'
READ_CONSISTENT = os.environ.get('READ_CONSISTENT', 'true').lower() == 'true'

DEFAULT_PAGE_LIMIT = int(os.environ.get('DEFAULT_PAGE_LIMIT', '50'))
MAX_PAGE_LIMIT = int(os.environ.get('MAX_PAGE_LIMIT', '500'))

# Auth configuration
AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'
MC_ENFORCE_NAMING = os.environ.get('MC_ENFORCE_NAMING', 'false').lower() == 'true'
MORAL_COMPASS_ALLOWED_SUFFIXES = os.environ.get('MORAL_COMPASS_ALLOWED_SUFFIXES', '-mc').split(',')
ALLOW_TABLE_DELETE = os.environ.get('ALLOW_TABLE_DELETE', 'false').lower() == 'true'
ALLOW_PUBLIC_READ = os.environ.get('ALLOW_PUBLIC_READ', 'true').lower() == 'true'

# Region configuration (using AWS_REGION_NAME to avoid conflict with AWS_REGION)
AWS_REGION_NAME = os.environ.get('AWS_REGION_NAME', os.environ.get('AWS_REGION', 'us-east-1'))

dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
table = dynamodb.Table(TABLE_NAME)

print(f"[BOOT] Using DynamoDB table: {TABLE_NAME} | SAFE_CONCURRENCY={SAFE_CONCURRENCY} | READ_CONSISTENT={READ_CONSISTENT}")
print(f"[BOOT] Auth config: AUTH_ENABLED={AUTH_ENABLED} | MC_ENFORCE_NAMING={MC_ENFORCE_NAMING} | ALLOW_TABLE_DELETE={ALLOW_TABLE_DELETE}")
print(f"[BOOT] Region: {AWS_REGION_NAME}")

_TABLE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

# ============================================================================
# Authentication & Authorization Helpers
# ============================================================================

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("[WARN] PyJWT not installed. JWT authentication will be disabled.")


def extract_token_from_event(event):
    """
    Extract JWT token from event headers.
    
    Checks Authorization header in order:
    1. headers.Authorization
    2. headers.authorization
    
    Returns:
        Optional[str]: Token string (without 'Bearer ' prefix) or None
    """
    headers = event.get('headers') or {}
    auth_header = headers.get('Authorization') or headers.get('authorization')
    
    if not auth_header:
        return None
    
    # Remove 'Bearer ' prefix if present
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    return auth_header


def decode_jwt_unverified(token):
    """
    Decode JWT token without signature verification.
    
    Note: This is a stub implementation. JWKS signature verification
    is planned for future work and should be implemented before
    production deployment in security-critical contexts.
    
    Args:
        token: JWT token string
    
    Returns:
        dict: Decoded claims or None if decode fails
    """
    if not JWT_AVAILABLE or not token:
        return None
    
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        return claims
    except Exception as e:
        print(f"[WARN] JWT decode failed: {e}")
        return None


def get_principal_from_claims(claims):
    """
    Derive principal identifier from JWT claims.
    
    Priority: cognito:username > email > sub
    
    Args:
        claims: Decoded JWT claims dict
    
    Returns:
        Optional[str]: Principal identifier or None
    """
    if not claims:
        return None
    
    return (
        claims.get('cognito:username') or
        claims.get('email') or
        claims.get('sub')
    )


def get_identity_from_event(event):
    """
    Extract identity information from event.
    
    Returns:
        dict: Identity info with keys: token, claims, principal, sub, email, issuer
              Returns empty dict if no valid identity found
    """
    identity = {}
    
    token = extract_token_from_event(event)
    if token:
        identity['token'] = token
        claims = decode_jwt_unverified(token)
        if claims:
            identity['claims'] = claims
            identity['principal'] = get_principal_from_claims(claims)
            identity['sub'] = claims.get('sub')
            identity['email'] = claims.get('email')
            identity['issuer'] = claims.get('iss')
    
    return identity


def is_owner(identity, owner_metadata):
    """
    Check if identity is the owner of a resource.
    
    Args:
        identity: Identity dict from get_identity_from_event
        owner_metadata: Dict containing ownerSub, ownerPrincipal, ownerEmail
    
    Returns:
        bool: True if identity matches owner
    """
    if not identity or not owner_metadata:
        return False
    
    # Match on sub, principal, or email
    identity_sub = identity.get('sub')
    identity_principal = identity.get('principal')
    identity_email = identity.get('email')
    
    owner_sub = owner_metadata.get('ownerSub')
    owner_principal = owner_metadata.get('ownerPrincipal')
    owner_email = owner_metadata.get('ownerEmail')
    
    # Check for matches
    if identity_sub and owner_sub and identity_sub == owner_sub:
        return True
    if identity_principal and owner_principal and identity_principal == owner_principal:
        return True
    if identity_email and owner_email and identity_email == owner_email:
        return True
    
    return False


def is_admin(identity):
    """
    Check if identity has admin privileges.
    
    Args:
        identity: Identity dict from get_identity_from_event
    
    Returns:
        bool: True if identity has admin role
    """
    if not identity or 'claims' not in identity:
        return False
    
    claims = identity['claims']
    groups = claims.get('cognito:groups', [])
    
    if isinstance(groups, list):
        return 'admin' in groups
    
    return False


def is_self(identity, username):
    """
    Check if identity matches the username.
    
    Args:
        identity: Identity dict from get_identity_from_event
        username: Username to check against
    
    Returns:
        bool: True if identity principal matches username
    """
    if not identity or not username:
        return False
    
    principal = identity.get('principal')
    return principal == username


def check_authorization(identity, owner_metadata=None, username=None, require_owner=False, require_self=False):
    """
    Check authorization for an operation.
    
    Args:
        identity: Identity dict from get_identity_from_event
        owner_metadata: Optional owner metadata for ownership checks
        username: Optional username for self checks
        require_owner: If True, requires owner or admin
        require_self: If True, requires self or admin
    
    Returns:
        bool: True if authorized
    """
    # Admin always authorized
    if is_admin(identity):
        return True
    
    # Check owner requirement
    if require_owner and owner_metadata:
        if is_owner(identity, owner_metadata):
            return True
        return False
    
    # Check self requirement
    if require_self and username:
        if is_self(identity, username):
            return True
        return False
    
    # If no specific requirement, deny if auth is enabled
    return not (require_owner or require_self)


def extract_playground_id(playground_url):
    """
    Extract playground ID from playground URL.
    
    Args:
        playground_url: URL of the playground
    
    Returns:
        Optional[str]: Playground ID or None if extraction fails
    
    Examples:
        https://example.com/playground/abc123 -> abc123
        https://example.com/playgrounds/abc123/edit -> abc123
    """
    if not playground_url:
        return None
    
    try:
        parsed = urlparse(playground_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Look for playground ID after 'playground' or 'playgrounds'
        for i, part in enumerate(path_parts):
            if part.lower() in ['playground', 'playgrounds']:
                if i + 1 < len(path_parts):
                    return path_parts[i + 1]
        
        # Fallback: use last path component if it looks like an ID
        if path_parts:
            last_part = path_parts[-1]
            if _TABLE_ID_RE.match(last_part):
                return last_part
        
        return None
    except Exception as e:
        print(f"[WARN] Failed to extract playground ID from URL {playground_url}: {e}")
        return None


def extract_region_from_table_id(table_id, playground_id):
    """
    Extract AWS region from a region-aware table ID.
    
    Args:
        table_id: The table ID (e.g., my-playground-us-east-1-mc)
        playground_id: The playground ID (e.g., my-playground)
    
    Returns:
        Optional[str]: Region name (e.g., us-east-1) or None if not region-aware
    
    Examples:
        extract_region_from_table_id('my-pg-us-east-1-mc', 'my-pg') -> 'us-east-1'
        extract_region_from_table_id('my-pg-mc', 'my-pg') -> None
    """
    if not table_id or not playground_id:
        return None
    
    # Check if table_id starts with playground_id
    if not table_id.startswith(playground_id):
        return None
    
    # Check for region-aware pattern: <playgroundId>-<region><suffix>
    for suffix in MORAL_COMPASS_ALLOWED_SUFFIXES:
        if table_id.startswith(playground_id + "-") and table_id.endswith(suffix):
            # Remove playground_id prefix and suffix
            middle = table_id[len(playground_id) + 1:-len(suffix)]
            # Validate region format
            if middle and re.match(r'^[a-z]{2}-[a-z]+-\d+$', middle):
                return middle
    
    return None


def validate_moral_compass_table_name(table_id, playground_id):
    """
    Validate moral compass table naming convention.
    
    Supports both region-aware and non-region-aware naming:
    - <playgroundId><suffix> (e.g., my-playground-mc)
    - <playgroundId>-<region><suffix> (e.g., my-playground-us-east-1-mc)
    
    Args:
        table_id: The requested table ID
        playground_id: The playground ID
    
    Returns:
        tuple: (is_valid: bool, error_message: Optional[str])
    """
    if not MC_ENFORCE_NAMING:
        return True, None
    
    # Check if table_id matches pattern: <playgroundId><suffix>
    for suffix in MORAL_COMPASS_ALLOWED_SUFFIXES:
        expected = f"{playground_id}{suffix}"
        if table_id == expected:
            return True, None
        
        # Check region-aware pattern: <playgroundId>-<region><suffix>
        # Extract potential region from table_id
        if table_id.startswith(playground_id + "-"):
            # Remove playground_id prefix
            remainder = table_id[len(playground_id) + 1:]
            # Check if remainder ends with the suffix
            if remainder.endswith(suffix):
                # Extract potential region (everything before the suffix)
                potential_region = remainder[:-len(suffix)]
                # Validate region format (alphanumeric with hyphens, e.g., us-east-1, eu-west-2)
                if potential_region and re.match(r'^[a-z]{2}-[a-z]+-\d+$', potential_region):
                    return True, None
    
    allowed_patterns = [f"{playground_id}{s}" for s in MORAL_COMPASS_ALLOWED_SUFFIXES]
    allowed_patterns_region = [f"{playground_id}-<region>{s}" for s in MORAL_COMPASS_ALLOWED_SUFFIXES]
    error = f"Invalid table name. Expected one of: {', '.join(allowed_patterns)} or {', '.join(allowed_patterns_region)}"
    return False, error

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
        'Access-Control-Allow-Methods': 'GET,PUT,PATCH,POST,DELETE,OPTIONS',
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
        playground_url = body.get('playgroundUrl')
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId. Must be alphanumeric with underscores/hyphens, max 64 chars'})
        
        # Extract identity if auth is enabled
        identity = {}
        if AUTH_ENABLED:
            identity = get_identity_from_event(event)
            if not identity.get('principal'):
                return create_response(401, {'error': 'Authentication required'})
        
        # Extract playground ID from URL if provided
        playground_id = None
        if playground_url:
            playground_id = extract_playground_id(playground_url)
            if not playground_id:
                return create_response(400, {'error': 'Invalid playgroundUrl. Could not extract playground ID'})
        
        # Validate naming convention for moral compass tables
        if MC_ENFORCE_NAMING and playground_id:
            is_valid, error_msg = validate_moral_compass_table_name(table_id, playground_id)
            if not is_valid:
                return create_response(400, {'error': error_msg})
        elif MC_ENFORCE_NAMING and not playground_id:
            # If naming enforcement is on but no playground URL provided, check if table follows pattern
            # This allows backward compatibility but warns
            has_mc_suffix = any(table_id.endswith(suffix) for suffix in MORAL_COMPASS_ALLOWED_SUFFIXES)
            if has_mc_suffix:
                return create_response(400, {
                    'error': 'playgroundUrl is required for moral compass tables when MC_ENFORCE_NAMING is enabled'
                })
        
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
        
        # Add ownership metadata if auth is enabled
        if AUTH_ENABLED and identity.get('principal'):
            metadata['ownerSub'] = identity.get('sub', '')
            metadata['ownerPrincipal'] = identity.get('principal', '')
            metadata['ownerEmail'] = identity.get('email', '')
            metadata['ownerIssuer'] = identity.get('issuer', '')
        
        # Add playground metadata if provided
        if playground_url:
            metadata['playgroundUrl'] = playground_url
        if playground_id:
            metadata['playgroundId'] = playground_id
            # Extract and store region if table uses region-aware naming
            region = extract_region_from_table_id(table_id, playground_id)
            if region:
                metadata['region'] = region
            else:
                # Store deployment region as default
                metadata['region'] = AWS_REGION_NAME
        
        retry_dynamo(lambda: table.put_item(Item=metadata))
        
        response_body = {
            'tableId': table_id,
            'displayName': display_name,
            'message': 'Table created successfully'
        }
        
        # Include ownership info in response if set
        if 'ownerPrincipal' in metadata:
            response_body['ownerPrincipal'] = metadata['ownerPrincipal']
        if 'playgroundId' in metadata:
            response_body['playgroundId'] = metadata['playgroundId']
        
        return create_response(201, response_body)
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"[ERROR] create_table exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def list_tables(event):
    """
    List table metadata items with stable descending ordering by createdAt (then tableId),
    supporting page-level limit and a synthetic lastKey.
    Ensures createdAt ordering is genuinely chronological (descending) across mixed formats:
      - epoch seconds (int)
      - epoch milliseconds (int)
      - epoch seconds with fractional part (float string)
      - ISO8601 strings with optional fractional seconds and trailing 'Z'
    Missing / unparseable createdAt values sort last.
    Default limit = 50 unless overridden by DEFAULT_TABLE_PAGE_LIMIT env var.
    
    Performance optimization: Uses GSI query when USE_METADATA_GSI=true to avoid full table scan.
    Logs structured metrics for observability.
    """
    start_time = time.time()
    try:
        params = (event.get('queryStringParameters') or {})

        default_limit = int(os.getenv('DEFAULT_TABLE_PAGE_LIMIT', '50'))
        raw_limit = params.get('limit')
        try:
            limit = int(raw_limit) if raw_limit is not None else default_limit
            if limit <= 0:
                raise ValueError
        except ValueError:
            return create_response(400, {'error': 'Invalid limit parameter'})

        raw_last_key = params.get('lastKey')
        start_after_table_id = None
        if raw_last_key:
            try:
                lk_obj = json.loads(raw_last_key)
                if isinstance(lk_obj, dict):
                    start_after_table_id = lk_obj.get('tableId')
                elif isinstance(lk_obj, str):
                    start_after_table_id = lk_obj
            except json.JSONDecodeError:
                start_after_table_id = raw_last_key

        use_gsi = os.getenv('USE_METADATA_GSI', 'false').lower() == 'true'
        # For list operations, use eventually consistent reads by default unless READ_CONSISTENT=true
        consistent_read = READ_CONSISTENT and not use_gsi  # GSI queries cannot use consistent reads

        metadata_items = []
        strategy = "scan"  # Track which path was used for metrics

        if use_gsi:
            strategy = "gsi_query"
            query_kwargs = {
                'IndexName': 'byUser',
                'KeyConditionExpression': Key('username').eq('_metadata')
                # Note: GSI queries do not support ConsistentRead parameter
            }
            while True:
                resp = retry_dynamo(lambda: table.query(**query_kwargs))
                metadata_items.extend(resp.get('Items', []))
                lek = resp.get('LastEvaluatedKey')
                if not lek:
                    break
                query_kwargs['ExclusiveStartKey'] = lek
        else:
            scan_kwargs = {
                'FilterExpression': Attr('username').eq('_metadata'),
                'ConsistentRead': consistent_read
            }
            while True:
                resp = retry_dynamo(lambda: table.scan(**scan_kwargs))
                metadata_items.extend(resp.get('Items', []))
                lek = resp.get('LastEvaluatedKey')
                if not lek:
                    break
                scan_kwargs['ExclusiveStartKey'] = lek

        from datetime import datetime, timezone

        def normalize_created_at(value):
            """
            Return milliseconds since epoch (int) for sortable comparison.
            Unparseable or missing -> -1.
            """
            if value is None:
                return -1

            # Already numeric
            if isinstance(value, (int, float)):
                # Heuristic: treat >10^12 as ms, else seconds.
                if isinstance(value, int):
                    if value >= 10**12:  # ms range
                        return value
                    elif value >= 10**9:  # seconds (approx current epoch seconds)
                        return value * 1000
                    else:
                        # Very small number, treat as seconds
                        return int(value * 1000)
                else:  # float
                    # float likely seconds with fractional
                    return int(round(value * 1000))

            if isinstance(value, str):
                s = value.strip()
                if not s:
                    return -1

                # Detect pure integer
                if s.isdigit():
                    iv = int(s)
                    if iv >= 10**12:      # milliseconds
                        return iv
                    elif iv >= 10**9:      # seconds
                        return iv * 1000
                    else:
                        return iv * 1000  # treat as seconds
                # Detect float numeric (seconds with fractional)
                try:
                    if all(c in "0123456789.+-" for c in s) and any(c == '.' for c in s):
                        fv = float(s)
                        return int(round(fv * 1000))
                except Exception:
                    pass

                # Attempt ISO8601
                try:
                    iso = s
                    # Common trailing Z for UTC
                    if iso.endswith('Z'):
                        iso = iso[:-1]  # strip Z; we'll attach UTC
                        dt = datetime.fromisoformat(iso)
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = datetime.fromisoformat(iso)
                        # If naive, assume UTC
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    return int(round(dt.timestamp() * 1000))
                except Exception:
                    # Could extend with additional parsing (e.g., dateutil) if needed.
                    return -1

            return -1

        # Sort descending by normalized createdAt then tableId
        metadata_items.sort(
            key=lambda it: (normalize_created_at(it.get('createdAt')), it.get('tableId', '')),
            reverse=True
        )

        start_index = 0
        if start_after_table_id:
            for idx, it in enumerate(metadata_items):
                if it.get('tableId') == start_after_table_id:
                    start_index = idx + 1
                    break

        page_slice = metadata_items[start_index:start_index + limit]

        tables = []
        for it in page_slice:
            tables.append({
                'tableId': it['tableId'],
                'displayName': it.get('displayName', it['tableId']),
                'createdAt': it.get('createdAt'),
                'isArchived': it.get('isArchived', False),
                'userCount': it.get('userCount', 0)
            })

        body = {'tables': tables}

        if start_index + limit < len(metadata_items) and page_slice:
            last_item = page_slice[-1]
            body['lastKey'] = {
                'tableId': last_item['tableId'],
                'username': '_metadata'
            }

        # Log structured metrics for observability
        duration_ms = int((time.time() - start_time) * 1000)
        metrics = {
            'metric': 'list_tables',
            'strategy': strategy,
            'consistentRead': consistent_read,
            'countFetched': len(metadata_items),
            'countReturned': len(tables),
            'limit': limit,
            'durationMs': duration_ms
        }
        print(json.dumps(metrics))

        return create_response(200, body)

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"[ERROR] list_tables createdAt ordering fix: {e} (duration: {duration_ms}ms)")
        return create_response(500, {'error': 'Internal server error'})

def get_table(event):
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        # Single item get can use eventually consistent read
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

def delete_table(event):
    """
    Delete a table and all associated user data.
    
    Authorization: Requires owner or admin when AUTH_ENABLED=true
    Feature flag: Only works when ALLOW_TABLE_DELETE=true
    """
    try:
        if not ALLOW_TABLE_DELETE:
            return create_response(403, {'error': 'Table deletion is disabled'})
        
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        
        # Get table metadata
        resp = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        
        if 'Item' not in resp:
            return create_response(404, {'error': 'Table not found'})
        
        metadata = resp['Item']
        
        # Check authorization if auth is enabled
        if AUTH_ENABLED:
            identity = get_identity_from_event(event)
            if not identity.get('principal'):
                return create_response(401, {'error': 'Authentication required'})
            
            # Check if user is owner or admin
            if not check_authorization(identity, owner_metadata=metadata, require_owner=True):
                return create_response(403, {'error': 'Only the table owner or admin can delete this table'})
        
        # Delete all items in the table (metadata + all users)
        # Query all items with this tableId
        deleted_count = 0
        query_kwargs = {
            'KeyConditionExpression': Key('tableId').eq(table_id)
        }
        
        while True:
            query_resp = retry_dynamo(lambda: table.query(**query_kwargs))
            items = query_resp.get('Items', [])
            
            # Delete items in batches
            for item in items:
                retry_dynamo(lambda i=item: table.delete_item(
                    Key={
                        'tableId': i['tableId'],
                        'username': i['username']
                    }
                ))
                deleted_count += 1
            
            # Check for more items
            last_key = query_resp.get('LastEvaluatedKey')
            if not last_key:
                break
            query_kwargs['ExclusiveStartKey'] = last_key
        
        print(f"[INFO] Deleted table {table_id} with {deleted_count} items")
        
        return create_response(200, {
            'message': f'Table {table_id} deleted successfully',
            'deletedItems': deleted_count
        })
    
    except Exception as e:
        print(f"[ERROR] delete_table exception: {e}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def list_users(event):
    """
    Paginated list of users with correct pagination logic.
    
    Performance optimization: Optionally uses leaderboard GSI when USE_LEADERBOARD_GSI=true
    for native ordering by submissionCount (requires GSI deployment).
    Logs structured metrics for observability.
    """
    start_time = time.time()
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        
        # For metadata check, can use eventually consistent read
        consistent_read_meta = READ_CONSISTENT
        meta = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=consistent_read_meta
        ))
        if 'Item' not in meta:
            return create_response(404, {'error': 'Table not found'})

        limit, exclusive_start_key = parse_pagination_params(event)
        
        use_leaderboard_gsi = os.getenv('USE_LEADERBOARD_GSI', 'false').lower() == 'true'
        strategy = "partition_query"  # Default strategy
        
        # For list operations, use eventually consistent reads by default
        consistent_read = READ_CONSISTENT
        
        if use_leaderboard_gsi:
            # Future enhancement: Query leaderboard GSI for native ordering
            # Note: DynamoDB GSI range keys only support ascending order
            # Would require storing negative submissionCount or fetching in reverse
            strategy = "leaderboard_gsi"
            # Placeholder - not fully implemented without actual GSI
            # For now, fall back to standard query
            print(f"[WARN] USE_LEADERBOARD_GSI=true but GSI not yet fully implemented, using standard query")
        
        query_kwargs = {
            'KeyConditionExpression': Key('tableId').eq(table_id),
            'Limit': limit + 2, 
            'ConsistentRead': consistent_read
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

        users_to_return = []
        for item in page_items:
            user_dict = {
                'username': item['username'],
                'submissionCount': item.get('submissionCount', 0),
                'totalCount': item.get('totalCount', 0),
                'lastUpdated': item.get('lastUpdated')
            }
            # Include moral compass fields if present
            if 'moralCompassScore' in item:
                user_dict['moralCompassScore'] = item['moralCompassScore']
            if 'metrics' in item:
                user_dict['metrics'] = item['metrics']
            if 'primaryMetric' in item:
                user_dict['primaryMetric'] = item['primaryMetric']
            if 'tasksCompleted' in item:
                user_dict['tasksCompleted'] = item['tasksCompleted']
            if 'totalTasks' in item:
                user_dict['totalTasks'] = item['totalTasks']
            if 'questionsCorrect' in item:
                user_dict['questionsCorrect'] = item['questionsCorrect']
            if 'totalQuestions' in item:
                user_dict['totalQuestions'] = item['totalQuestions']
            users_to_return.append(user_dict)
        
        # Sort by moralCompassScore if present, otherwise by submissionCount
        def sort_key(x):
            # Primary: moralCompassScore (descending), fallback: submissionCount (descending)
            moral_score = float(x.get('moralCompassScore', 0))
            submission_count = x.get('submissionCount', 0)
            return (moral_score, submission_count)
        
        users_to_return.sort(key=sort_key, reverse=True)
        
        # Log structured metrics for observability
        duration_ms = int((time.time() - start_time) * 1000)
        metrics = {
            'metric': 'list_users',
            'strategy': strategy,
            'consistentRead': consistent_read,
            'countFetched': len(user_items),
            'countReturned': len(users_to_return),
            'limit': limit,
            'durationMs': duration_ms,
            'tableId': table_id
        }
        print(json.dumps(metrics))
        
        return create_response(200, build_paged_body('users', users_to_return, response_last_key))
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"[ERROR] list_users exception: {e} (duration: {duration_ms}ms)")
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
        
        # Get table metadata
        meta = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in meta:
            return create_response(404, {'error': 'Table not found'})
        
        # Check authorization if auth is enabled
        if AUTH_ENABLED:
            identity = get_identity_from_event(event)
            if not identity.get('principal'):
                return create_response(401, {'error': 'Authentication required'})
            
            # Allow self or admin to update user data
            if not check_authorization(identity, username=username, require_self=True):
                return create_response(403, {'error': 'Only the user or admin can update this data'})
        
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
        
        # Add submitter metadata on first write if auth is enabled
        if AUTH_ENABLED and identity.get('principal'):
            # Get existing user data
            existing_resp = retry_dynamo(lambda: table.get_item(
                Key={'tableId': table_id, 'username': username},
                ConsistentRead=READ_CONSISTENT
            ))
            existing_item = existing_resp.get('Item', {})
            
            # Set submitter metadata if not already present (backward compatibility)
            if not existing_item.get('submitterSub'):
                user_data['submitterSub'] = identity.get('sub', '')
                user_data['submitterPrincipal'] = identity.get('principal', '')
                user_data['submitterEmail'] = identity.get('email', '')
        
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

def put_user_moral_compass(event):
    """
    Update user's moral compass score with dynamic metrics.
    
    Payload fields:
    - metrics: dict of metric_name -> numeric_value
    - primaryMetric: optional string indicating which metric is primary (defaults to 'accuracy' or first sorted key)
    - tasksCompleted: int
    - totalTasks: int
    - questionsCorrect: int
    - totalQuestions: int
    
    Computes: moralCompassScore = primaryMetricValue * ((tasksCompleted + questionsCorrect) / (totalTasks + totalQuestions))
    """
    try:
        params = event.get('pathParameters') or {}
        table_id = params.get('tableId')
        username = params.get('username')
        body = json.loads(event.get('body', '{}'))
        
        if not validate_table_id(table_id):
            return create_response(400, {'error': 'Invalid tableId format'})
        if not validate_username(username):
            return create_response(400, {'error': 'Invalid username format'})
        
        # Verify table exists
        meta = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': '_metadata'},
            ConsistentRead=READ_CONSISTENT
        ))
        if 'Item' not in meta:
            return create_response(404, {'error': 'Table not found'})
        
        # Check authorization if auth is enabled
        if AUTH_ENABLED:
            identity = get_identity_from_event(event)
            if not identity.get('principal'):
                return create_response(401, {'error': 'Authentication required'})
            
            # Allow self or admin to update moral compass data
            if not check_authorization(identity, username=username, require_self=True):
                return create_response(403, {'error': 'Only the user or admin can update this data'})
        else:
            identity = {}
        
        # Extract and validate payload
        metrics = body.get('metrics')
        primary_metric = body.get('primaryMetric')
        tasks_completed = body.get('tasksCompleted')
        total_tasks = body.get('totalTasks')
        questions_correct = body.get('questionsCorrect')
        total_questions = body.get('totalQuestions')
        
        # Validate metrics
        if not metrics or not isinstance(metrics, dict):
            return create_response(400, {'error': 'metrics must be a non-empty dict'})
        
        # Validate all metric values are numeric and convert to Decimal
        metrics_decimal = {}
        try:
            for key, value in metrics.items():
                if not isinstance(value, (int, float, Decimal)):
                    return create_response(400, {'error': f'Metric {key} must be numeric'})
                metrics_decimal[key] = Decimal(str(value))
        except Exception as e:
            return create_response(400, {'error': f'Invalid metric values: {str(e)}'})
        
        # Determine primary metric
        if primary_metric:
            if primary_metric not in metrics_decimal:
                return create_response(400, {'error': f'primaryMetric "{primary_metric}" not found in metrics'})
        else:
            # Default: 'accuracy' if present, else first sorted key
            if 'accuracy' in metrics_decimal:
                primary_metric = 'accuracy'
            else:
                primary_metric = sorted(metrics_decimal.keys())[0]
        
        primary_metric_value = metrics_decimal[primary_metric]
        
        # Validate progress fields
        try:
            tasks_completed = int(tasks_completed) if tasks_completed is not None else 0
            total_tasks = int(total_tasks) if total_tasks is not None else 0
            questions_correct = int(questions_correct) if questions_correct is not None else 0
            total_questions = int(total_questions) if total_questions is not None else 0
        except (ValueError, TypeError):
            return create_response(400, {'error': 'Progress fields must be integers'})
        
        if any(x < 0 for x in [tasks_completed, total_tasks, questions_correct, total_questions]):
            return create_response(400, {'error': 'Progress fields must be non-negative'})
        
        # Compute moral compass score
        progress_denominator = total_tasks + total_questions
        if progress_denominator == 0:
            moral_compass_score = Decimal('0.0')
        else:
            progress_ratio = Decimal(tasks_completed + questions_correct) / Decimal(progress_denominator)
            moral_compass_score = primary_metric_value * progress_ratio
        
        # Get existing user data to preserve submissionCount/totalCount if present
        existing_resp = retry_dynamo(lambda: table.get_item(
            Key={'tableId': table_id, 'username': username},
            ConsistentRead=READ_CONSISTENT
        ))
        existing_item = existing_resp.get('Item', {})
        
        # Build user data
        user_data = {
            'tableId': table_id,
            'username': username,
            'metrics': metrics_decimal,
            'primaryMetric': primary_metric,
            'tasksCompleted': tasks_completed,
            'totalTasks': total_tasks,
            'questionsCorrect': questions_correct,
            'totalQuestions': total_questions,
            'moralCompassScore': moral_compass_score,
            'lastUpdated': datetime.utcnow().isoformat(),
            # Preserve existing submission counts if present
            'submissionCount': existing_item.get('submissionCount', 0),
            'totalCount': existing_item.get('totalCount', 0)
        }
        
        # Add submitter metadata on first write if auth is enabled and not already present
        if AUTH_ENABLED and identity.get('principal') and not existing_item.get('submitterSub'):
            user_data['submitterSub'] = identity.get('sub', '')
            user_data['submitterPrincipal'] = identity.get('principal', '')
            user_data['submitterEmail'] = identity.get('email', '')
        
        created_new = 'username' not in existing_item
        
        # Store to DynamoDB
        retry_dynamo(lambda: table.put_item(Item=user_data))
        
        # Increment user count if new user
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
            'metrics': metrics,
            'primaryMetric': primary_metric,
            'moralCompassScore': float(moral_compass_score),
            'tasksCompleted': tasks_completed,
            'totalTasks': total_tasks,
            'questionsCorrect': questions_correct,
            'totalQuestions': total_questions,
            'message': 'Moral compass data updated successfully',
            'createdNew': created_new
        })
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"[ERROR] put_user_moral_compass exception: {e}")
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
        elif route_key == 'DELETE /tables/{tableId}':
            return delete_table(event)
        elif route_key == 'GET /tables/{tableId}/users':
            return list_users(event)
        elif route_key == 'GET /tables/{tableId}/users/{username}':
            return get_user(event)
        elif route_key == 'PUT /tables/{tableId}/users/{username}':
            return put_user(event)
        elif route_key == 'PUT /tables/{tableId}/users/{username}/moral-compass':
            return put_user_moral_compass(event)
        elif route_key == 'PUT /tables/{tableId}/users/{username}/moralcompass':
            return put_user_moral_compass(event)
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
        elif method == 'DELETE' and path.startswith('/tables/') and path.count('/') == 2:
            return delete_table(event)
        elif method == 'GET' and path.endswith('/users') and path.count('/') == 3:
            return list_users(event)
        elif method == 'GET' and '/users/' in path and path.count('/') == 4:
            return get_user(event)
        elif method == 'PUT' and '/users/' in path and '/moral-compass' in path and path.count('/') == 5:
            return put_user_moral_compass(event)
        elif method == 'PUT' and '/users/' in path and '/moralcompass' in path and path.count('/') == 5:
            return put_user_moral_compass(event)
        elif method == 'PUT' and '/users/' in path and path.count('/') == 4:
            return put_user(event)
        elif method == 'GET' and path == '/health':
            return health(event)

        return create_response(404, {'error': 'Route not found'})
    except Exception as e:
        print(f"[ERROR] handler unexpected exception: {e}")
        return create_response(500, {'error': f'Unexpected error: {str(e)}'})
