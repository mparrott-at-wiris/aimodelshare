import os
import boto3
import botocore
import requests
import json
import base64
from aimodelshare.exceptions import AuthorizationError, AWSAccessError
from aimodelshare.modeluser import get_jwt_token

def set_credentials(credential_file=None, type="submit_model", apiurl="apiurl", manual = True, cloud="aws"):
  import os
  import getpass
  from aimodelshare.aws import get_aws_token
  from aimodelshare.modeluser import get_jwt_token, setup_bucket_only
  if all([credential_file==None, type=="submit_model"]):
    set_credentials_public(type="submit_model", apiurl=apiurl)
    os.environ["AWS_TOKEN"]=get_aws_token()
  elif all([credential_file==None, type=="deploy_model", cloud=="model_share"]):
    set_credentials_public_aimscloud(credential_file=None, type="deploy_model", apiurl=apiurl)
    os.environ["cloud_location"] = cloud
  else:
      ##TODO: Require that "type" is provided, to ensure correct env vars get loaded
      flag = False

      # Set AI Modelshare Username & Password
      if all([manual == True, credential_file==None]):
        user = getpass.getpass(prompt="Modelshare.ai Username:")
        os.environ["username"] = user
        pw = getpass.getpass(prompt="Modelshare.ai Password:")
        os.environ["password"] = pw
        
      else: 
        f = open(credential_file)

        for line in f:
          if "aimodelshare_creds" in line or "AIMODELSHARE_CREDS" in line:
            for line in f:
              if line == "\n":
                break
              try:
                value = line.split("=", 1)[1].strip()
                value = value[1:-1]
                key = line.split("=", 1)[0].strip()
                os.environ[key.lower()] = value

              except LookupError: 
                print(* "Warning: Review format of", credential_file, ". Format should be variablename = 'variable_value'")
                break
      
      #Validate Username & Password
      try: 
        os.environ["AWS_TOKEN"]=get_aws_token()

        print("Modelshare.ai login credentials set successfully.")
      except: 
        print("Credential confirmation unsuccessful. Check username & password and try again.")
        return
      
      # Set AWS Creds Manually (submit or deploy)
      if  all([manual == True,credential_file==None]):
        flag = True
        access_key = getpass.getpass(prompt="AWS_ACCESS_KEY_ID:")
        os.environ["AWS_ACCESS_KEY_ID"] = access_key
        os.environ["AWS_ACCESS_KEY_ID_AIMS"] = access_key

        secret_key = getpass.getpass(prompt="AWS_SECRET_ACCESS_KEY:")
        os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
        os.environ["AWS_SECRET_ACCESS_KEY_AIMS"] = secret_key

        region = getpass.getpass(prompt="AWS_REGION:")
        os.environ["AWS_REGION"] = region
        os.environ["AWS_REGION_AIMS"] = region

      # Set AWS creds from file
      else:  
        f = open(credential_file)
        if type == "submit_model": 
          for line in f:
            if (apiurl in line) and ((type in line) or (type.upper() in line)): ## searches on apiurl AND type
              flag = True
              for line in f:
                if line == "\n":
                  break
                try:
                  value = line.split("=", 1)[1].strip()
                  value = value[1:-1]
                  key = line.split("=", 1)[0].strip()
                  os.environ[key.upper()] = value
                except LookupError: 
                  print(* "Warning: Review format of", credential_file, ". Format should be variablename = 'variable_value'.")
                  break

        elif type == "deploy_model": 
          for line in f:
            if ((type in line) or (type.upper() in line)):  ## only searches on type
              flag = True
              for line in f:
                if line == "\n":
                  break
                try:
                  value = line.split("=", 1)[1].strip()
                  value = value[1:-1]
                  key = line.split("=", 1)[0].strip()
                  os.environ[key.upper()] = value
                except LookupError: 
                  print(* "Warning: Review format of", credential_file, ". Format should be variablename = 'variable_value'.")
                  break

      if "AWS_ACCESS_KEY_ID_AIMS" in os.environ:
        pass
      elif "AWS_ACCESS_KEY_ID" in os.environ:
          os.environ['AWS_ACCESS_KEY_ID_AIMS']=os.environ.get("AWS_ACCESS_KEY_ID")
      if "AWS_SECRET_ACCESS_KEY_AIMS" in os.environ:
        pass
      elif "AWS_SECRET_ACCESS_KEY" in os.environ:
          os.environ['AWS_SECRET_ACCESS_KEY_AIMS']=os.environ.get("AWS_SECRET_ACCESS_KEY")

      if 'AWS_REGION_AIMS' in os.environ:
        pass
      elif "AWS_REGION" in os.environ:
          os.environ['AWS_REGION_AIMS']=os.environ.get("AWS_REGION")
      # Validate AWS Creds 
      import boto3
      try: 
        client = boto3.client('sts', aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"))
        details = client.get_caller_identity()
        print("AWS credentials set successfully.")
      except: 
        print("AWS credential confirmation unsuccessful. Check AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY and try again.")
        return
      
      # Set Environment Variables for deploy models
      if type == "deploy_model":
        get_jwt_token(os.environ.get("username"), os.environ.get("password"))
        setup_bucket_only()  # Use new function that doesn't create IAM users  
        
      if not flag: 
        print("Error: apiurl or type not found in"+str(credential_file)+". Please correct entries and resubmit.")
      
      try:
        f.close()
      except:
        pass

  return

def set_credentials_public(credential_file=None, type="submit_model", apiurl="apiurl", manual = True):
  import os
  import getpass
  from aimodelshare.aws import get_aws_token
  from aimodelshare.modeluser import get_jwt_token, setup_bucket_only

  ##TODO: Require that "type" is provided, to ensure correct env vars get loaded
  flag = False

  # Set AI Modelshare Username & Password
  if all([manual == True, credential_file==None]):
    user = getpass.getpass(prompt="Modelshare.ai Username:")
    os.environ["username"] = user
    pw = getpass.getpass(prompt="Modelshare.ai Password:")
    os.environ["password"] = pw
  
  else: 
    f = open(credential_file)

    for line in f:
      if "aimodelshare_creds" in line or "AIMODELSHARE_CREDS" in line:
        for line in f:
          if line == "\n":
            break
          try:
            value = line.split("=", 1)[1].strip()
            value = value[1:-1]
            key = line.split("=", 1)[0].strip()
            os.environ[key.lower()] = value

          except LookupError: 
            print(* "Warning: Review format of", credential_file, ". Format should be variablename = 'variable_value'")
            break
    if "AWS_ACCESS_KEY_ID_AIMS" in os.environ:
      pass
    elif "AWS_ACCESS_KEY_ID" in os.environ:
        os.environ['AWS_ACCESS_KEY_ID_AIMS']=os.environ.get("AWS_ACCESS_KEY_ID")
    if "AWS_SECRET_ACCESS_KEY_AIMS" in os.environ:
      pass
    elif "AWS_SECRET_ACCESS_KEY" in os.environ:
        os.environ['AWS_SECRET_ACCESS_KEY_AIMS']=os.environ.get("AWS_SECRET_ACCESS_KEY")

    if 'AWS_REGION_AIMS' in os.environ:
      pass
    elif "AWS_REGION" in os.environ:
        os.environ['AWS_REGION_AIMS']=os.environ.get("AWS_REGION")
  #Validate Username & Password
  try: 
    os.environ["AWS_TOKEN"]=get_aws_token()

    print("Modelshare.ai login credentials set successfully.")
  except: 
    print("Credential confirmation unsuccessful. Check username & password and try again.")
    return
  
   # Set AWS creds from file
 
  try:
    f.close()
  except:
    pass

  return

def set_credentials_public_aimscloud(credential_file=None, type="deploy_model", apiurl="apiurl", manual = True):
  import os
  import getpass
  from aimodelshare.aws import get_aws_token
  from aimodelshare.modeluser import get_jwt_token, setup_bucket_only

  ##TODO: Require that "type" is provided, to ensure correct env vars get loaded
  flag = False

  # Set AI Modelshare Username & Password
  if all([manual == True, credential_file==None]):
    user = getpass.getpass(prompt="Modelshare.ai Username:")
    os.environ["username"] = user
    pw = getpass.getpass(prompt="Modelshare.ai Password:")
    os.environ["password"] = pw
  
  else: 
    f = open(credential_file)

    for line in f:
      if "aimodelshare_creds" in line or "AIMODELSHARE_CREDS" in line:
        for line in f:
          if line == "\n":
            break
          try:
            value = line.split("=", 1)[1].strip()
            value = value[1:-1]
            key = line.split("=", 1)[0].strip()
            os.environ[key.lower()] = value

          except LookupError: 
            print(* "Warning: Review format of", credential_file, ". Format should be variablename = 'variable_value'")
            break
    if "AWS_ACCESS_KEY_ID_AIMS" in os.environ:
      pass
    elif "AWS_ACCESS_KEY_ID" in os.environ:
        os.environ['AWS_ACCESS_KEY_ID_AIMS']=os.environ.get("AWS_ACCESS_KEY_ID")
    if "AWS_SECRET_ACCESS_KEY_AIMS" in os.environ:
      pass
    elif "AWS_SECRET_ACCESS_KEY" in os.environ:
        os.environ['AWS_SECRET_ACCESS_KEY_AIMS']=os.environ.get("AWS_SECRET_ACCESS_KEY")

    if 'AWS_REGION_AIMS' in os.environ:
      pass
    elif "AWS_REGION" in os.environ:
        os.environ['AWS_REGION_AIMS']=os.environ.get("AWS_REGION")
  #Validate Username & Password
  try: 
    os.environ["AWS_TOKEN"]=get_aws_token()
    get_jwt_token(user,pw)
    print("Modelshare.ai login credentials set successfully.")
  except: 
    print("Credential confirmation unsuccessful. Check username & password and try again.")
    return
  
   # Set AWS creds from file
 
  try:
    f.close()
  except:
    pass

  return

def get_aws_token():
    config = botocore.config.Config(signature_version=botocore.UNSIGNED)

    provider_client = boto3.client(
        "cognito-idp", region_name="us-east-2", config=config
    )

    try:
        response = provider_client.initiate_auth(
            ClientId="7ptv9f8pt36elmg0e4v9v7jo9t",
            AuthFlow="USER_PASSWORD_AUTH",
             AuthParameters={"USERNAME": os.getenv('username'), "PASSWORD": os.getenv('password')},
        )

    except Exception as err:
        raise AuthorizationError("Could not authorize user. " + str(err))

    return response["AuthenticationResult"]["IdToken"]


def get_token_from_session(session_id):
    """
    Retrieve AWS JWT token from session API endpoint.
    
    Args:
        session_id: The session identifier from URL parameter
        
    Returns:
        str: JWT token if session is valid
        
    Raises:
        AuthorizationError: If session is invalid or API request fails
    """
    try:
        # NOTE: This URL should be configured via environment variable or config file
        # Update AIMODELSHARE_SESSION_API_URL environment variable to override
        session_api_url = os.getenv(
            "AIMODELSHARE_SESSION_API_URL",
            f"https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev/sessions/{session_id}"
        )
        
        response = requests.get(session_api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        token = data.get("token") or data.get("id_token") or data.get("IdToken")
        
        if not token:
            raise AuthorizationError("No token found in session API response")
            
        return token
        
    except requests.RequestException as err:
        raise AuthorizationError(f"Failed to retrieve token from session: {err}")
    except (KeyError, ValueError) as err:
        raise AuthorizationError(f"Invalid session API response: {err}")


def _get_username_from_token(token):
    """
    Extract username from JWT token claims.
    
    Args:
        token: JWT token string
        
    Returns:
        str: Username extracted from 'cognito:username' or 'username' claim, or None if not found
    """
    try:
        # JWT tokens have 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None
            
        # Decode the payload (second part)
        # Add padding if needed for base64 decoding
        payload = parts[1]
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
            
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        
        # Try different possible username claim names
        # Note: 'sub' is excluded as it's typically a UUID, not a human-readable username
        username = claims.get('cognito:username') or claims.get('username')
        
        return username
        
    except (ValueError, json.JSONDecodeError, KeyError, IndexError) as err:
        print(f"Warning: Could not extract username from token: {err}")
        return None


def get_aws_session(aws_key=None, aws_secret=None, aws_region=None):
    session = boto3.Session(
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=aws_region
    )

def get_aws_client(aws_key=None, aws_secret=None, aws_region=None):
    key = aws_key if aws_key is not None else os.environ.get("AWS_ACCESS_KEY_ID_AIMS")
    secret = (
        aws_secret
        if aws_secret is not None
        else os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS")
    )
    region = (
        aws_region if aws_region is not None else os.environ.get("AWS_REGION_AIMS") #changed
    )

    if any([key is None, secret is None, region is None]):
        raise ValueError("Invalid arguments")

    usersession = boto3.session.Session(
        aws_access_key_id=key, aws_secret_access_key=secret, region_name=region,
    )

    s3client = usersession.client("s3")
    s3resource = usersession.resource("s3")

    return {"client": s3client, "resource": s3resource}


def get_s3_iam_client(aws_key=None,aws_password=None, aws_region=None):

  key = aws_key if aws_key is not None else os.environ.get("AWS_ACCESS_KEY_ID_AIMS")
  password = (
        aws_password
        if aws_password is not None
        else os.environ.get("AWS_SECRET_ACCESS_KEY_AIMS"))
  region = (
        aws_region if aws_region is not None else os.environ.get("AWS_REGION_AIMS")) #changed

  if any([key is None, password is None, region is None]):
        raise AuthorizationError("Please set your aws credentials before creating your prediction API.")

  usersession = boto3.session.Session(
        aws_access_key_id=key, aws_secret_access_key=password, region_name=region,
    )

  s3_client = boto3.client('s3' , region_name ="us-east-1")
  s3_resource = boto3.resource('s3')
  iam_client = boto3.client('iam')
  iam_resource = boto3.resource('iam')

  s3 = {"client":s3_client,"resource":s3_resource}
  iam = {"client":iam_client,"resource":iam_resource}

  return s3,iam,region


def run_function_on_lambda(url, username=None, token=None, **kwargs):
    if username==None:
      kwargs["apideveloper"] = os.environ.get("username")
    else:
      kwargs["apideveloper"] = username
    kwargs["apiurl"] = url
    if token==None:
      headers_with_authentication = {
          "content-type": "application/json",
          "authorizationToken": os.environ.get("AWS_TOKEN"),
      }
    else:
      headers_with_authentication = {
          "content-type": "application/json",
          "authorizationToken": token,
      }

    response = requests.post(
        "https://bhrdesksak.execute-api.us-east-1.amazonaws.com/dev/modeldata",
        json=kwargs,
        headers=headers_with_authentication,
    )

    if response.status_code != 200:
        return (
            None,
            AWSAccessError(
                "Error:"
                + "Please make sure your api url and token are correct."
            ),
        )

    return response, None


def get_token(username, password):
      #get token for access to prediction lambas or to submit predictions to generate model evaluation metrics
      tokenstring = '{\"username\": \"$usernamestring\", \"password\": \"$passwordstring\"}'
      from string import Template
      t = Template(tokenstring)
      newdata = t.substitute(
          usernamestring=username, passwordstring=password)
      api_url='https://xgwe1d6wai.execute-api.us-east-1.amazonaws.com/dev' 
      headers={ 'Content-Type':'application/json'}
      token =requests.post(api_url,headers=headers,data=json.dumps({"action": "login", "request":newdata}))
      return token.text

def configure_credentials(): 
    import getpass
    user = getpass.getpass(prompt="Modelshare.ai Username:")
    pw = getpass.getpass(prompt="Modelshare.ai Password:")
    input_AWS_ACCESS_KEY_ID = getpass.getpass(prompt="AWS_ACCESS_KEY_ID:")
    input_AWS_SECRET_ACCESS_KEY = getpass.getpass(prompt="AWS_SECRET_ACCESS_KEY:")
    input_AWS_REGION = getpass.getpass(prompt="AWS_REGION:")
    
    
    #Format output text
    formatted_userpass = ('[aimodelshare_creds] \n'
                          'username = "' + user + '"\n'
                          'password = "' + pw + '"\n\n')

    formatted_new_creds = ("#Deploy Credentials \n"
                    '[deploy_model]\n'
                    'AWS_ACCESS_KEY_ID = "' + input_AWS_ACCESS_KEY_ID + '"\n'
                    'AWS_SECRET_ACCESS_KEY = "' + input_AWS_SECRET_ACCESS_KEY +'"\n'
                    'AWS_REGION = "' + input_AWS_REGION + '"\n')
    
    # Generate .txt file with new credentials 
    f= open("credentials.txt","w+")
    f.write(formatted_userpass + formatted_new_creds)
    f.close()
    
    return print("Configuration successful. New credentials file saved as 'credentials.txt'")

__all__ = [
    get_aws_token,
    get_aws_client,
    run_function_on_lambda,
    get_s3_iam_client,
    set_credentials,
    configure_credentials,
    set_credentials_public
]
