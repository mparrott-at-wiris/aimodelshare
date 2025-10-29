import boto3
import botocore
import os
import requests
import uuid
import json
import math
import time
import datetime
import regex as re
from aimodelshare.exceptions import AuthorizationError, AWSAccessError, AWSUploadError

def decode_token_unverified(token: str):
    """Decode a JWT without verifying signature or audience, compatible with PyJWT<2 and >=2 versions.
    
    Parameters
    ----------
    token : str
        The JWT token to decode
    
    Returns
    -------
    dict
        The decoded token payload
    """
    import jwt
    try:
        return jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    except TypeError:
        # PyJWT >=2 may require specifying algorithms if verification is enabled; here we keep it disabled
        return jwt.decode(token, options={"verify_signature": False, "verify_aud": False}, algorithms=["HS256"])


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

def setup_bucket_only():
    """
    Set up the S3 bucket for aimodelshare without creating new IAM users.
    
    Uses the provided AWS credentials to create or access the bucket.
    This avoids creating a new IAM user every time credentials are set.
    """
    from aimodelshare.aws import get_s3_iam_client

    s3, iam, region = get_s3_iam_client(os.environ.get("AWS_ACCESS_KEY_ID_AIMS"), 
                                        os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"), 
                                        os.environ.get("AWS_REGION_AIMS"))
    
    user_session = boto3.session.Session(aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID_AIMS"),
                                         aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"), 
                                         region_name= os.environ.get("AWS_REGION_AIMS"))    
    
    account_number = user_session.client(
        'sts').get_caller_identity().get('Account')

    # Remove special characters from username
    username_clean = re.sub('[^A-Za-z0-9-]+', '', os.environ.get("username"))
    bucket_name = 'aimodelshare' + username_clean.lower() + str(account_number) + region.replace('-', '')
    
    region = os.environ.get("AWS_REGION_AIMS")
    s3_client = s3['client']

    # Create bucket if it doesn't exist
    try:
        response = s3_client.head_bucket(Bucket=bucket_name)
    except:
        if region == "us-east-1":
            response = s3_client.create_bucket(
                ACL="private",
                Bucket=bucket_name
            )
        else:
            location = {'LocationConstraint': region}
            response = s3_client.create_bucket(
                ACL="private",
                Bucket=bucket_name,
                CreateBucketConfiguration=location
            )

    # Set the bucket name in environment for use by other functions
    os.environ["BUCKET_NAME"] = bucket_name
    
    return


def create_user_getkeyandpassword():
    """
    DEPRECATED: This function creates a new IAM user every time it's called.
    
    Use setup_bucket_only() instead, which uses the provided AWS credentials
    without creating new IAM users and policies.
    
    This function is kept for backward compatibility but should not be used.
    """
    import warnings
    warnings.warn(
        "create_user_getkeyandpassword() is deprecated and creates unnecessary IAM users. "
        "Use setup_bucket_only() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
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
    try:
        response=s3_client.head_bucket(Bucket=bucket_name)
    except:
        if(region=="us-east-1"):
            response = s3_client.create_bucket(
                ACL="private",
                Bucket=bucket_name
            )
        else:
            location={'LocationConstraint': region}
            response=s3_client.create_bucket(
                ACL="private",
                Bucket=bucket_name,
                CreateBucketConfiguration=location
            )

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
    get_jwt_token,
    create_user_getkeyandpassword,
    setup_bucket_only,
    decode_token_unverified,
]
