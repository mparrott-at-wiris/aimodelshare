import boto3
import botocore
import os
import requests
import uuid
import json
import math
import time
import datetime
import warnings
import regex as re
from aimodelshare.exceptions import AuthorizationError, AWSAccessError, AWSUploadError
from aimodelshare import iam_utils

def get_jwt_token(username, password):

    config = botocore.config.Config(signature_version=botocore.UNSIGNED)

    provider_client = boto3.client(
      "cognito-idp", region_name="us-east-2", config=config
    )

    try:
      # Get JWT token for the user
      response = provider_client.initiate_auth(
        ClientId='25vssbned2bbaoi1q7rs4i914u',
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={'USERNAME': username,'PASSWORD': password})

      os.environ["JWT_AUTHORIZATION_TOKEN"] = response["AuthenticationResult"]["IdToken"]

    except :
      err = "Username or password does not exist.  Please enter new username or password."+"\n"
      err += "Sign up at AImodelshare.com/register."
      raise AuthorizationError(err)

    return 

def get_execution_session(role_arn=None):
    """
    Get a boto3 session using STS AssumeRole for ephemeral credentials.
    
    This function replaces the creation of long-term IAM users with temporary
    STS sessions, improving security through ephemeral credentials.
    
    Args:
        role_arn: ARN of the role to assume. If None, reads from environment
                  variable AIMODELSHARE_EXECUTION_ROLE_ARN.
    
    Returns:
        boto3.Session: Session with temporary credentials from AssumeRole
        
    Raises:
        ValueError: If role_arn is not provided and environment variable is not set
        AWSAccessError: If AssumeRole fails
    """
    if role_arn is None:
        role_arn = os.environ.get("AIMODELSHARE_EXECUTION_ROLE_ARN")
    
    if not role_arn:
        raise ValueError(
            "AIMODELSHARE_EXECUTION_ROLE_ARN environment variable must be set "
            "or role_arn must be provided to use STS AssumeRole sessions."
        )
    
    try:
        # Create base session with user credentials
        base_session = boto3.session.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID_AIMS"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"),
            region_name=os.environ.get("AWS_REGION_AIMS")
        )
        
        sts_client = base_session.client('sts')
        
        # Assume the role
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"aimodelshare-session-{int(time.time())}",
            DurationSeconds=3600  # 1 hour session
        )
        
        credentials = response['Credentials']
        
        # Create session with temporary credentials
        assumed_session = boto3.session.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=os.environ.get("AWS_REGION_AIMS")
        )
        
        return assumed_session
        
    except Exception as err:
        raise AWSAccessError(f"Failed to assume role {role_arn}: {str(err)}")

def create_user_getkeyandpassword(use_ephemeral_users=False):
    """
    Create IAM user and access keys (deprecated) or setup execution role.
    
    Args:
        use_ephemeral_users: If True, uses the deprecated IAM user creation path.
                            If False (default), expects AIMODELSHARE_EXECUTION_ROLE_ARN
                            to be set for AssumeRole-based authentication.
    
    Note:
        The use_ephemeral_users=True option is deprecated and will be removed in a future version.
        Please migrate to using STS AssumeRole with AIMODELSHARE_EXECUTION_ROLE_ARN.
    """
    if use_ephemeral_users:
        warnings.warn(
            "Creating ephemeral IAM users is deprecated and will be removed in a future version. "
            "Please set AIMODELSHARE_EXECUTION_ROLE_ARN environment variable and use "
            "STS AssumeRole for better security and resource management.",
            DeprecationWarning,
            stacklevel=2
        )
        _create_user_getkeyandpassword_legacy()
    else:
        # New path: Verify execution role is configured
        if not os.environ.get("AIMODELSHARE_EXECUTION_ROLE_ARN"):
            raise ValueError(
                "AIMODELSHARE_EXECUTION_ROLE_ARN environment variable must be set. "
                "Alternatively, set use_ephemeral_users=True to use deprecated IAM user creation "
                "(not recommended for production)."
            )
        # The actual session will be created when needed via get_execution_session()
        return

def _create_user_getkeyandpassword_legacy():

    from aimodelshare.bucketpolicy import _custom_s3_policy
    from aimodelshare.tools import form_timestamp
    from aimodelshare.aws import get_s3_iam_client

    s3, iam, region = get_s3_iam_client(os.environ.get("AWS_ACCESS_KEY_ID_AIMS"), 
                                        os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"), 
                                        os.environ.get("AWS_REGION_AIMS"))
    
    #create s3 bucket and iam user
    now = datetime.datetime.now()
    year = datetime.date.today().year
    ts = form_timestamp(time.time())
    
    user_session = boto3.session.Session(aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID_AIMS"),
                                         aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"), 
                                         region_name= os.environ.get("AWS_REGION_AIMS"))    
    
    account_number = user_session.client(
        'sts').get_caller_identity().get('Account')

    #Remove special characters from username
    username_clean = re.sub('[^A-Za-z0-9-]+', '', os.environ.get("username"))
    bucket_name = 'aimodelshare' + username_clean.lower()+str(account_number) + region.replace('-', '')
    master_name = 'aimodelshare' + username_clean.lower()+str(account_number)
    from botocore.client import ClientError

    region = os.environ.get("AWS_REGION_AIMS")

    s3_client = s3['client']

    s3_client, bucket_name, region = s3['client'], bucket_name, region
    # Use iam_utils.ensure_bucket for consistency
    iam_utils.ensure_bucket(s3_client, bucket_name, region)

    my_policy = _custom_s3_policy(bucket_name)
    #sub_bucket = 'aimodelshare' + username.lower() + ts.replace("_","")
    iam_username = 'AI_MODELSHARE_' + ts
    
    try:
      
      iam["client"].create_user(
        UserName = iam_username
      )
      iam_response = iam["client"].create_access_key(
        UserName=iam_username
      )
    except Exception as err:
      raise err

    os.environ["AI_MODELSHARE_ACCESS_KEY_ID"] = iam_response['AccessKey']['AccessKeyId']
    os.environ["AI_MODELSHARE_SECRET_ACCESS_KEY"] = iam_response['AccessKey']['SecretAccessKey']
    
    #create and attach policy for the s3 bucket
    my_managed_policy = _custom_s3_policy(bucket_name)
    policy_name = 'temporaryaccessAImodelsharePolicy' + str(uuid.uuid1().hex)
    policy_response = iam["client"].create_policy(
      PolicyName = policy_name,
      PolicyDocument = json.dumps(my_managed_policy)
    )
    policy_arn = policy_response['Policy']['Arn']
    user = iam["resource"].User(iam_username)
    user.attach_policy(
          PolicyArn=policy_arn
      )
    
    os.environ["IAM_USERNAME"] = iam_username
    os.environ["POLICY_ARN"] = policy_arn
    os.environ["POLICY_NAME"] = policy_name
    os.environ["BUCKET_NAME"] = bucket_name
 
    return 

__all__ = [
    'get_jwt_token',
    'create_user_getkeyandpassword',
    'get_execution_session',
]
