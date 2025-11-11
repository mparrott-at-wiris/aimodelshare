import os
import boto3
import json
import onnx
import numpy as np
import pandas as pd
import requests 
import json
import ast
import tensorflow as tf
import tempfile as tmp
from datetime import datetime
try:
    import torch
except:
    pass

from aimodelshare.leaderboard import get_leaderboard
from aimodelshare.aws import run_function_on_lambda, get_token, get_aws_token, get_aws_client
from aimodelshare.aimsonnx import _get_leaderboard_data, inspect_model, _get_metadata, _model_summary, model_from_string, pyspark_model_from_string, _get_layer_names, _get_layer_names_pytorch
from aimodelshare.aimsonnx import model_to_onnx
from aimodelshare.utils import ignore_warning
import warnings


def _normalize_eval_payload(raw_eval):
    """
    Normalize the API response eval payload to (public_eval_dict, private_eval_dict).
    
    Handles multiple response formats:
    - {"eval": [public_dict, private_dict]}  -> extract both dicts
    - {"eval": public_dict}                   -> public_dict, {}
    - {"eval": None} or missing              -> {}, {}
    - Malformed responses                     -> {}, {} with warning
    
    Args:
        raw_eval: The raw API response (expected to be dict with 'eval' key)
        
    Returns:
        tuple: (public_eval_dict, private_eval_dict) - both guaranteed to be dicts
    """
    public_eval = {}
    private_eval = {}
    
    if not isinstance(raw_eval, dict):
        print("---------------------------------------------------------------")
        print(f"--- WARNING: API response is not a dict (type={type(raw_eval)}) ---")
        print("Defaulting to empty eval metrics.")
        print("---------------------------------------------------------------")
        return public_eval, private_eval
    
    eval_field = raw_eval.get('eval')
    
    if eval_field is None:
        # No eval field present
        return public_eval, private_eval
    
    if isinstance(eval_field, list):
        # Expected format: [public_dict, private_dict, ...]
        if len(eval_field) >= 1 and isinstance(eval_field[0], dict):
            public_eval = eval_field[0]
        if len(eval_field) >= 2 and isinstance(eval_field[1], dict):
            private_eval = eval_field[1]
        elif len(eval_field) >= 1:
            # Only one dict in list, treat as public
            if not public_eval:
                public_eval = {}
    elif isinstance(eval_field, dict):
        # Single dict, treat as public eval
        public_eval = eval_field
    else:
        print("---------------------------------------------------------------")
        print(f"--- WARNING: 'eval' field has unexpected type: {type(eval_field)} ---")
        print("Defaulting to empty eval metrics.")
        print("---------------------------------------------------------------")
    
    return public_eval, private_eval


def _subset_numeric(metrics_dict, keys_to_extract):
    """
    Safely extract a subset of numeric metrics from a metrics dictionary.
    
    Args:
        metrics_dict: Dictionary containing metric key-value pairs
        keys_to_extract: List of keys to extract from the dictionary
        
    Returns:
        dict: Subset of metrics that exist and have numeric (float/int) values
    """
    if not isinstance(metrics_dict, dict):
        print("---------------------------------------------------------------")
        print(f"--- WARNING: metrics_dict is not a dict (type={type(metrics_dict)}) ---")
        print("Returning empty metrics subset.")
        print("---------------------------------------------------------------")
        return {}
    
    subset = {}
    for key in keys_to_extract:
        value = metrics_dict.get(key)
        if value is not None and isinstance(value, (int, float)):
            subset[key] = value
    
    return subset


def _prepare_preprocessor_if_function(preprocessor, debug_mode=False):
    """Prepare a preprocessor for submission.
    Accepts:
      - None: returns None
      - Path to existing preprocessor zip (.zip)
      - Callable function: exports source or pickled callable with loader
      - Transformer object (e.g., sklearn Pipeline/ColumnTransformer) with .transform: pickles object + loader
    Returns: absolute path to created or existing preprocessor zip, or None.
    Raises: RuntimeError with actionable message on failure.
    """
    import inspect
    import tempfile
    import zipfile
    import pickle
    import textwrap
    
    if preprocessor is None:
        return None

    # Existing zip path
    if isinstance(preprocessor, str) and preprocessor.endswith('.zip'):
        if not os.path.exists(preprocessor):
            raise RuntimeError(f"Preprocessor export failed: zip path not found: {preprocessor}")
        if debug_mode:
            print(f"[DEBUG] Using existing preprocessor zip: {preprocessor}")
        return preprocessor

    # Determine if transformer object
    is_transformer_obj = hasattr(preprocessor, 'transform') and not inspect.isfunction(preprocessor)

    serialize_object = None
    export_callable = None

    if is_transformer_obj:
        if debug_mode:
            print('[DEBUG] Detected transformer object; preparing wrapper.')
        transformer_obj = preprocessor

        def _wrapped_preprocessor(data):
            return transformer_obj.transform(data)
        export_callable = _wrapped_preprocessor
        serialize_object = transformer_obj  # pickle the transformer

    elif callable(preprocessor):
        export_callable = preprocessor
    else:
        raise RuntimeError(
            f"Preprocessor export failed: Unsupported type {type(preprocessor)}. "
            "Provide a callable, transformer with .transform, an existing .zip path, or None."
        )

    tmp_dir = tempfile.mkdtemp()
    py_path = os.path.join(tmp_dir, 'preprocessor.py')
    zip_path = os.path.join(tmp_dir, 'preprocessor.zip')
    pkl_name = 'preprocessor.pkl'

    source_written = False
    # Attempt direct source extraction if not a transformer serialization
    if serialize_object is None:
        try:
            src = inspect.getsource(export_callable)
            with open(py_path, 'w') as f:
                f.write(src)
            source_written = True
            if debug_mode:
                print('[DEBUG] Wrote source for callable preprocessor.')
        except Exception as e:
            if debug_mode:
                print(f'[DEBUG] Source extraction failed; falling back to pickled callable: {e}')
            serialize_object = export_callable  # fallback to pickling callable

    # If transformer or fallback pickled callable: write loader stub
    if serialize_object is not None and not source_written:
        loader_stub = textwrap.dedent(f"""
        import pickle, os
        _PKL_FILE = '{pkl_name}'
        _loaded_obj = None
        def preprocessor(data):
            global _loaded_obj
            if _loaded_obj is None:
                with open(os.path.join(os.path.dirname(__file__), _PKL_FILE), 'rb') as pf:
                    _loaded_obj = pickle.load(pf)
            # If original object was a transformer it has .transform; else callable
            if hasattr(_loaded_obj, 'transform'):
                return _loaded_obj.transform(data)
            return _loaded_obj(data)
        """)
        with open(py_path, 'w') as f:
            f.write(loader_stub)
        if debug_mode:
            print('[DEBUG] Wrote loader stub for pickled object.')

    # Serialize object if needed
    if serialize_object is not None:
        try:
            with open(os.path.join(tmp_dir, pkl_name), 'wb') as pf:
                pickle.dump(serialize_object, pf)
            if debug_mode:
                print('[DEBUG] Pickled transformer/callable successfully.')
        except Exception as e:
            raise RuntimeError(f'Preprocessor export failed: pickling failed: {e}')

    # Create zip
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(py_path, arcname='preprocessor.py')
            pkl_path = os.path.join(tmp_dir, pkl_name)
            if os.path.exists(pkl_path):
                zf.write(pkl_path, arcname=pkl_name)
    except Exception as e:
        raise RuntimeError(f'Preprocessor export failed: zip creation error: {e}')

    # Final validation
    if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
        raise RuntimeError(f'Preprocessor export failed: zip file not found or empty at {zip_path}')

    if debug_mode:
        print(f'[DEBUG] Preprocessor zip created: {zip_path}')
    return zip_path


def _diagnose_closure_variables(preprocessor_fxn):
    """
    Diagnose closure variables for serialization issues.
    
    Args:
        preprocessor_fxn: Function to diagnose
        
    Logs:
        INFO for successful serialization of each closure object
        WARNING for failed serialization attempts
    """
    import inspect
    import pickle
    import logging
    
    # Get closure variables
    closure_vars = inspect.getclosurevars(preprocessor_fxn)
    all_globals = closure_vars.globals
    
    if not all_globals:
        logging.info("No closure variables detected in preprocessor function")
        return
    
    logging.info(f"Analyzing {len(all_globals)} closure variables...")
    
    successful = []
    failed = []
    
    for var_name, var_value in all_globals.items():
        try:
            # Attempt to pickle the object
            pickle.dumps(var_value)
            successful.append(var_name)
            logging.info(f"✓ Closure variable '{var_name}' (type: {type(var_value).__name__}) is serializable")
        except Exception as e:
            failed.append((var_name, type(var_value).__name__, str(e)))
            logging.warning(f"✗ Closure variable '{var_name}' (type: {type(var_value).__name__}) failed serialization: {e}")
    
    # Summary
    if failed:
        failure_summary = "; ".join([f"{name} ({vtype})" for name, vtype, _ in failed])
        logging.warning(f"Serialization failures detected: {failure_summary}")
    else:
        logging.info(f"All {len(successful)} closure variables are serializable")
    
    return successful, failed


def _get_file_list(client, bucket,keysubfolderid):
    #  Reading file list {{{
    try:
        objectlist=[]
        paginator = client.get_paginator('list_objects')
        pages = paginator.paginate(Bucket=bucket, Prefix=keysubfolderid)

        for page in pages:
            for obj in page['Contents']:
                objectlist.append(obj['Key'])

    except Exception as err:
        return None, err

    file_list = []
    for key in objectlist:
            file_list.append(key.split("/")[-1])
    #  }}}

    return file_list, None


def _delete_s3_object(client, bucket, model_id, filename):
    deletionobject = client["resource"].Object(bucket, model_id + "/" + filename)
    deletionobject.delete()

def _get_predictionmodel_key(unique_model_id,file_extension):
    if file_extension==".pkl":
        file_key = unique_model_id + "/runtime_model" + file_extension
        versionfile_key = unique_model_id + "/predictionmodel_1" + file_extension
    else:
        file_key = unique_model_id + "/runtime_model" + file_extension
        versionfile_key = unique_model_id + "/predictionmodel_1" + file_extension
    return file_key,versionfile_key


def _upload_onnx_model(modelpath, client, bucket, model_id, model_version):
    # Check the model {{{
    if not os.path.exists(modelpath):
        raise FileNotFoundError(f"The model file at {modelpath} does not exist")

    file_name = os.path.basename(modelpath)
    file_name, file_ext = os.path.splitext(file_name)

    assert (
        file_ext == ".onnx"
    ), "modelshareai api only supports .onnx models at the moment"
    # }}}

    # Upload the model {{{
    try:
        client["client"].upload_file(
            modelpath, bucket, model_id + "/onnx_model_mostrecent.onnx"
        )
        client["client"].upload_file(
            modelpath,
            bucket,
            model_id + "/onnx_model_v" + str(model_version) + file_ext,
        )
    except Exception as err:
        return err
    # }}}

def _upload_native_model(modelpath, client, bucket, model_id, model_version):
    # Check the model {{{
    if not os.path.exists(modelpath):
        raise FileNotFoundError(f"The model file at {modelpath} does not exist")

    file_name = os.path.basename(modelpath)
    file_name, file_ext = os.path.splitext(file_name)

    assert (
        file_ext == ".onnx"
    ), "modelshareai api only supports .onnx models at the moment"
    # }}}

    # Upload the model {{{
    try:
        client["client"].upload_file(
            modelpath, bucket, model_id + "/onnx_model_mostrecent.onnx"
        )
        client["client"].upload_file(
            modelpath,
            bucket,
            model_id + "/onnx_model_v" + str(model_version) + file_ext,
        )
    except Exception as err:
        return err
    # }}}


def _upload_preprocessor(preprocessor, client, bucket, model_id, model_version):

  try:

    
    # Check the preprocessor {{{
    if not os.path.exists(preprocessor):
        raise FileNotFoundError(
            f"The preprocessor file at {preprocessor} does not exist"
        )

    
    file_name = os.path.basename(preprocessor)
    file_name, file_ext = os.path.splitext(file_name)
    
    from zipfile import ZipFile
    dir_zip = preprocessor

    #zipObj = ZipFile(os.path.join("./preprocessor.zip"), 'a')
    #/Users/aishwarya/Downloads/aimodelshare-master
    client["client"].upload_file(dir_zip, bucket, model_id + "/preprocessor_v" + str(model_version)+ ".zip")
  except Exception as e:
    print(e)


def _update_leaderboard_public(
    modelpath,
    eval_metrics,
    s3_presigned_dict,
    custom_metadata=None,
    private=False,
    leaderboard_type="competition",
    onnx_model=None,
):
    """
    Update the public (or private) leaderboard file via presigned URLs.
    Adds new columns if custom_metadata introduces new keys.
    """
    mastertable_path = (
        "model_eval_data_mastertable_private.csv"
        if private
        else "model_eval_data_mastertable.csv"
    )

    # Load or derive metadata
    if modelpath is not None and not os.path.exists(modelpath):
        raise FileNotFoundError(f"The model file at {modelpath} does not exist")

    model_versions = [
        os.path.splitext(f)[0].split("_")[-1][1:]
        for f in s3_presigned_dict["put"].keys()
    ]
    model_versions = list(map(int, filter(lambda v: v.isnumeric(), model_versions)))
    model_version = model_versions[0]

    if onnx_model is not None:
        metadata = _get_leaderboard_data(onnx_model, eval_metrics)
    elif modelpath is not None:
        onnx_model = onnx.load(modelpath)
        metadata = _get_leaderboard_data(onnx_model, eval_metrics)
    else:
        metadata = _get_leaderboard_data(None, eval_metrics)

    if custom_metadata:
        metadata = {**metadata, **custom_metadata}

    metadata["username"] = os.environ.get("username")
    metadata["timestamp"] = str(datetime.now())
    metadata["version"] = model_version

    temp_dir = tmp.mkdtemp()

    # Read existing leaderboard (if any)
    try:
        import wget

        wget.download(
            s3_presigned_dict["get"][mastertable_path],
            out=os.path.join(temp_dir, mastertable_path),
        )
        leaderboard = pd.read_csv(
            os.path.join(temp_dir, mastertable_path), sep="\t"
        )
    except Exception:
        leaderboard = pd.DataFrame(columns=list(metadata.keys()))

    # Expand columns for any new metadata keys
    existing_cols = set(leaderboard.columns.tolist())
    new_cols = [c for c in metadata.keys() if c not in existing_cols]
    for c in new_cols:
        leaderboard[c] = None

    # Append row
    row_dict = {col: metadata.get(col, None) for col in leaderboard.columns}
    leaderboard.loc[len(leaderboard)] = row_dict

    # Legacy behavior: remove model_config from metadata dict before returning
    metadata.pop("model_config", None)

    # Write updated leaderboard to temp
    leaderboard.to_csv(
        os.path.join(temp_dir, mastertable_path), index=False, sep="\t"
    )

    # Upload via appropriate presigned POST
    try:
        put_keys = list(s3_presigned_dict["put"].keys())
        csv_put_entries = [k for k in put_keys if "csv" in k]

        file_put_dicts = [
            ast.literal_eval(s3_presigned_dict["put"][k]) for k in csv_put_entries
        ]
        # public uses first, private uses second
        target_index = 1 if private else 0
        upload_spec = file_put_dicts[target_index]

        with open(os.path.join(temp_dir, mastertable_path), "rb") as f:
            files = {"file": (mastertable_path, f)}
            http_response = requests.post(
                upload_spec["url"], data=upload_spec["fields"], files=files
            )
            if http_response.status_code not in (200, 204):
                raise RuntimeError(
                    f"Leaderboard upload failed with status {http_response.status_code}: {http_response.text}"
                )

        return metadata
    except Exception as err:
        return err


def _update_leaderboard(
    modelpath,
    eval_metrics,
    client,
    bucket,
    model_id,
    model_version,
    onnx_model=None,
    custom_metadata=None,
):
    """
    Update the leaderboard directly in S3 using boto3 client/resource (non-presigned path).
    Adds new columns if custom_metadata introduces new keys.
    """
    # Build metadata
    if onnx_model is not None:
        metadata = _get_leaderboard_data(onnx_model, eval_metrics)
    elif modelpath is not None:
        if not os.path.exists(modelpath):
            raise FileNotFoundError(f"The model file at {modelpath} does not exist")
        loaded = onnx.load(modelpath)
        metadata = _get_leaderboard_data(loaded, eval_metrics)
    else:
        metadata = _get_leaderboard_data(None, eval_metrics)

    if custom_metadata:
        metadata = {**metadata, **custom_metadata}

    metadata["username"] = os.environ.get("username")
    metadata["timestamp"] = str(datetime.now())
    metadata["version"] = model_version

    # Fetch existing leaderboard (if any)
    try:
        obj = client["client"].get_object(
            Bucket=bucket, Key=model_id + "/model_eval_data_mastertable.csv"
        )
        leaderboard = pd.read_csv(obj["Body"], sep="\t")
    except client["client"].exceptions.NoSuchKey:
        leaderboard = pd.DataFrame(columns=list(metadata.keys()))
    except Exception as err:
        raise err

    # Expand columns as needed
    existing_cols = set(leaderboard.columns.tolist())
    new_cols = [c for c in metadata.keys() if c not in existing_cols]
    for c in new_cols:
        leaderboard[c] = None

    # Append row
    row_dict = {col: metadata.get(col, None) for col in leaderboard.columns}
    leaderboard.loc[len(leaderboard)] = row_dict

    # Legacy removal
    metadata.pop("model_config", None)

    # Write and upload
    csv_payload = leaderboard.to_csv(index=False, sep="\t")
    try:
        s3_object = client["resource"].Object(
            bucket, model_id + "/model_eval_data_mastertable.csv"
        )
        s3_object.put(Body=csv_payload)
        return metadata
    except Exception as err:
        return err
 

def _normalize_model_config(model_config, model_type=None):
    """
    Normalize model_config to a dict, handling various input types.
    
    Args:
        model_config: Can be None, dict, or string representation of dict
        model_type: Optional model type for context in warnings
        
    Returns:
        dict: Normalized model config, or empty dict if normalization fails
    """
    import ast
    
    # If already a dict, return as-is
    if isinstance(model_config, dict):
        return model_config
    
    # If None or other non-string type, return empty dict
    if not isinstance(model_config, str):
        if model_config is not None:
            print(f"Warning: model_config is {type(model_config).__name__}, expected str or dict. Using empty config.")
        return {}
    
    # Try to parse string to dict
    try:
        import astunparse
        
        tree = ast.parse(model_config)
        stringconfig = model_config
        
        # Find and quote callable nodes
        problemnodes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                problemnodes.append(astunparse.unparse(node).replace("\n", ""))
        
        problemnodesunique = set(problemnodes)
        for i in problemnodesunique:
            stringconfig = stringconfig.replace(i, "'" + i + "'")
        
        # Parse the modified string
        model_config_dict = ast.literal_eval(stringconfig)
        return model_config_dict if isinstance(model_config_dict, dict) else {}
        
    except Exception as e:
        print(f"Warning: Failed to parse model_config string: {e}. Using empty config.")
        return {}


def _build_sklearn_param_dataframe(model_type, model_config):
    """
    Build parameter inspection DataFrame for sklearn/xgboost models.
    
    Creates a DataFrame with aligned columns by taking the union of default
    parameters and model_config parameters. This ensures equal-length arrays
    even when model_config contains extra parameters or is missing defaults.
    
    Args:
        model_type: String name of the sklearn model class
        model_config: Dict of model configuration parameters
        
    Returns:
        pd.DataFrame: DataFrame with param_name, default_value, param_value columns,
                     or empty DataFrame on error
    """
    import pandas as pd
    import warnings
    
    try:
        model_class = model_from_string(model_type)
        default_instance = model_class()
        defaults_dict = default_instance.get_params()
        
        # Take union of keys from both sources to ensure all parameters are included
        # This prevents ValueError: "All arrays must be of the same length"
        # when model_config has different keys than defaults
        param_names = sorted(set(defaults_dict.keys()) | set(model_config.keys()))
        default_values = [defaults_dict.get(k, None) for k in param_names]
        param_values = [model_config.get(k, None) for k in param_names]
        
        return pd.DataFrame({
            'param_name': param_names,
            'default_value': default_values,
            'param_value': param_values
        })
    except Exception as e:
        # Log warning and fallback to empty DataFrame
        warnings.warn(f"Failed to instantiate model class for {model_type}: {e}")
        return pd.DataFrame()


def upload_model_dict(modelpath, s3_presigned_dict, bucket, model_id, model_version, placeholder=False, onnx_model=None):
    import wget
    import json
    import ast
    temp=tmp.mkdtemp()
    # get model summary from onnx
    import astunparse

    if placeholder==False: 

        if onnx_model==None:
            onnx_model = onnx.load(modelpath)
        meta_dict = _get_metadata(onnx_model)

        if meta_dict['ml_framework'] in ['keras', 'pytorch']:

            inspect_pd = _model_summary(meta_dict)
            
        elif meta_dict['ml_framework'] in ['sklearn', 'xgboost']:

            # Normalize model_config to dict (handles None, dict, or string)
            model_config = _normalize_model_config(
                meta_dict.get("model_config"), 
                meta_dict.get('model_type')
            )
            
            # Build parameter inspection DataFrame
            inspect_pd = _build_sklearn_param_dataframe(
                meta_dict['model_type'], 
                model_config
            )

        elif meta_dict['ml_framework'] in ['pyspark']:
            
            # Normalize model_config to dict (handles None, dict, or string)
            model_config_temp = _normalize_model_config(
                meta_dict.get("model_config"), 
                meta_dict.get('model_type')
            )

            try:
                model_class = pyspark_model_from_string(meta_dict['model_type'])
                default = model_class()

                # get model config dict from pyspark model object
                default_config_temp = {}
                for key, value in default.extractParamMap().items():
                    default_config_temp[key.name] = value
                
                # Sort the keys so default and model config key matches each other
                model_config = dict(sorted(model_config_temp.items()))
                default_config = dict(sorted(default_config_temp.items()))
                
                model_configkeys = model_config.keys()
                model_configvalues = model_config.values()
                default_config = default_config.values()
            except:
                model_class = str(pyspark_model_from_string(meta_dict['model_type']))
                if model_class.find("Voting") > 0:
                    default_config = ["No data available"]
                    model_configkeys = ["No data available"]
                    model_configvalues = ["No data available"]
                else:
                    # Fallback for other exceptions
                    default_config = []
                    model_configkeys = []
                    model_configvalues = []

            inspect_pd = pd.DataFrame({'param_name': model_configkeys,
                                        'default_value': default_config,
                                        'param_value': model_configvalues})

    else:
        meta_dict = {}
        meta_dict['ml_framework'] = "undefined"
        meta_dict['model_type'] = "undefined"

        #inspect_pd = pd.DataFrame({' ':["No metadata available for this model"]})
        inspect_pd = pd.DataFrame()
   
    try:
        #Get inspect json
        inspectdatafilename = wget.download(s3_presigned_dict['get']['inspect_pd_'+str(model_version)+'.json'], out=temp+"/"+'inspect_pd_'+str(model_version)+'.json')
        
        with open(temp+"/"+'inspect_pd_'+str(model_version)+'.json') as f:
            model_dict  = json.load(f)
    except: 
        model_dict = {}

    model_dict[str(model_version)] = {'ml_framework': meta_dict['ml_framework'],
                                      'model_type': meta_dict['model_type'],
                                      'model_dict': inspect_pd.to_dict()}

    with open(temp+"/"+'inspect_pd_'+str(model_version)+'.json', 'w') as outfile:
        json.dump(model_dict, outfile)

    try:

      putfilekeys=list(s3_presigned_dict['put'].keys())
      modelputfiles = [s for s in putfilekeys if str('inspect_pd_'+str(model_version)+'.json') in s]

      fileputlistofdicts=[]
      for i in modelputfiles:
        filedownload_dict=ast.literal_eval(s3_presigned_dict ['put'][i])
        fileputlistofdicts.append(filedownload_dict)

      with open(temp+"/"+'inspect_pd_'+str(model_version)+'.json', 'rb') as f:
        files = {'file': (temp+"/"+'inspect_pd_'+str(model_version)+'.json', f)}
        http_response = requests.post(fileputlistofdicts[0]['url'], data=fileputlistofdicts[0]['fields'], files=files)
    except:
      pass
    return 1


def upload_model_graph(modelpath, s3_presigned_dict, bucket, model_id, model_version, onnx_model=None):
    import wget
    import json
    import ast
    temp=tmp.mkdtemp()
    # get model summary from onnx

    if onnx_model==None:
        onnx_model = onnx.load(modelpath)

    meta_dict = _get_metadata(onnx_model)

    if meta_dict['ml_framework'] == 'keras':

        model_graph = meta_dict['model_graph']

    if meta_dict['ml_framework'] == 'pytorch':

        model_graph = ''

    elif meta_dict['ml_framework'] in ['sklearn', 'xgboost', 'pyspark']:

        model_graph = ''

    key = model_id+'/model_graph_'+str(model_version)+'.json'
    
    try:
        #Get inspect json
        modelgraphdatafilename = wget.download(s3_presigned_dict['get']['model_graph_'+str(model_version)+'.json'], out=temp+"/"+'model_graph_'+str(model_version)+'.json')

        with open(temp+"/"+'model_graph_'+str(model_version)+'.json') as f:
            graph_dict  = json.load(f)

    except: 
        graph_dict = {}

    graph_dict[str(model_version)] = {'ml_framework': meta_dict['ml_framework'],
                                      'model_type': meta_dict['model_type'],
                                      'model_graph': model_graph}

    with open(temp+"/"+'model_graph_'+str(model_version)+'.json', 'w') as outfile:
        json.dump(graph_dict, outfile)

    try:

      putfilekeys=list(s3_presigned_dict['put'].keys())
      modelputfiles = [s for s in putfilekeys if str('model_graph_'+str(model_version)+'.json') in s]

      fileputlistofdicts=[]
      for i in modelputfiles:
        filedownload_dict=ast.literal_eval(s3_presigned_dict ['put'][i])
        fileputlistofdicts.append(filedownload_dict)

      with open(temp+"/"+'model_graph_'+str(model_version)+'.json', 'rb') as f:
        files = {'file': (temp+"/"+'model_graph_'+str(model_version)+'.json', f)}
        http_response = requests.post(fileputlistofdicts[0]['url'], data=fileputlistofdicts[0]['fields'], files=files)
    except:
      pass

    return 1


def submit_model(
    model_filepath=None,
    apiurl=None,
    prediction_submission=None,
    preprocessor=None,
    reproducibility_env_filepath=None,
    custom_metadata=None,
    submission_type="competition",
    input_dict = None,
    print_output=True,
    debug_preprocessor=False
    ):
    """
    Submits model/preprocessor to machine learning competition using live prediction API url generated by AI Modelshare library
    The submitted model gets evaluated and compared with all existing models and a leaderboard can be generated 
    ---------------
    Parameters:
    modelpath:  string ends with '.onnx'
                value - Absolute path to model file [REQUIRED] to be set by the user
                .onnx is the only accepted model file extension
                "example_model.onnx" filename for file in directory.
                "/User/xyz/model/example_model.onnx" absolute path to model file from local directory
    apiurl :    string 
                value - url to the live prediction REST API generated for the user's model 
                "https://example.execute-api.us-east-1.amazonaws.com/prod/m"
    prediction_submission:   one hot encoded y_pred
                    value - predictions for test data
                    [REQUIRED] for evaluation metriicts of the submitted model
    preprocessor:   string,default=None
                    value - absolute path to preprocessor file 
                    [REQUIRED] to be set by the user
                    "./preprocessor.zip" 
                    searches for an exported zip preprocessor file in the current directory
                    file is generated from preprocessor module using export_preprocessor function from the AI Modelshare library 
    reproducibility_env_filepath: string
                                value - absolute path to environment environment json file 
                                [OPTIONAL] to be set by the user
                                "./reproducibility.json" 
                                file is generated using export_reproducibility_env function from the AI Modelshare library
    debug_preprocessor: boolean, default=False
                        value - enable detailed diagnostics for preprocessor closure variable serialization
                        [OPTIONAL] when True, logs detailed information about which closure variables 
                        succeeded or failed serialization
    -----------------
    Returns
    response:   Model version if the model is submitted sucessfully
                error  if there is any error while submitting models
    
    """

    # catch missing model_input for pytorch 
    try:
        import torch
        if isinstance(model_filepath, torch.nn.Module) and model_input==None:
            raise ValueError("Please submit valid model_input for pytorch model.")
    except:
        pass


    # check whether preprocessor is function and validate export
    preprocessor = _prepare_preprocessor_if_function(preprocessor, debug_mode=debug_preprocessor)



    import os
    from aimodelshare.aws import get_aws_token
    from aimodelshare.modeluser import get_jwt_token
    import ast

    # Confirm that creds are loaded, raise error if not
    # NOTE: Replaced 'return print(...)' with raise to prevent silent None propagation
    if not all(["username" in os.environ, 
                "password" in os.environ]):
        raise RuntimeError("'Submit Model' unsuccessful. Please provide username and password using set_credentials() function.")


    ##---Step 2: Get bucket and model_id for playground and check prediction submission structure

    apiurl=apiurl.replace('"','')

    # Get bucket and model_id for user {{{
    response, error = run_function_on_lambda(
        apiurl, **{"delete": "FALSE", "versionupdateget": "TRUE"}
    )
    if error is not None:
        raise error

    _, bucket, model_id = json.loads(response.content.decode("utf-8"))
    # }}}

    #begin replacing code here
    #add call to eval lambda here to retrieve presigned urls and eval metrics
    if prediction_submission is not None:
        if type(prediction_submission) is not list:
            prediction_submission=prediction_submission.tolist()
        else: 
            pass

        if all(isinstance(x, (np.float64)) for x in prediction_submission):
              prediction_submission = [float(i) for i in prediction_submission]
        else: 
            pass

    ##---Step 3: Attempt to get eval metrics and file access dict for model leaderboard submission
    #includes checks if returned values a success and errors otherwise

    import os
    import pickle
    temp = tmp.mkdtemp()
    predictions_path = temp + "/" + 'predictions.pkl'

    fileObject = open(predictions_path, 'wb')
    pickle.dump(prediction_submission, fileObject)
    predfilesize=os.path.getsize(predictions_path)

    fileObject.close()

    if predfilesize>3555000:

        post_dict = {"y_pred": [],
              "return_eval_files": "True",
              "submission_type": submission_type,
              "return_y": "False"}

        headers = { 'Content-Type':'application/json', 'authorizationToken': json.dumps({"token":os.environ.get("AWS_TOKEN"),"eval":"TEST"}), } 
        apiurl_eval=apiurl[:-1]+"eval"
        predictionfiles = requests.post(apiurl_eval,headers=headers,data=json.dumps(post_dict)) 
        eval_metrics=json.loads(predictionfiles.text)

        s3_presigned_dict = {key:val for key, val in eval_metrics.items() if key != 'eval'}

        idempotentmodel_version=s3_presigned_dict['idempotentmodel_version']
        s3_presigned_dict.pop('idempotentmodel_version')
            #upload preprocessor (1s for small upload vs 21 for 306 mbs)
        putfilekeys=list(s3_presigned_dict['put'].keys())
        modelputfiles = [s for s in putfilekeys if str("pkl") in s]

        fileputlistofdicts=[]
        for i in modelputfiles:
          filedownload_dict=ast.literal_eval(s3_presigned_dict ['put'][i])
          fileputlistofdicts.append(filedownload_dict)


        with open(predictions_path , 'rb') as f:
                files = {'file': (predictions_path , f)} 
                http_response = requests.post(fileputlistofdicts[0]['url'], data=fileputlistofdicts[0]['fields'], files=files)
                f.close()

        post_dict = {"y_pred": [],
                    "predictionpklname":fileputlistofdicts[0]['fields']['key'].split("/")[2],
                "submission_type": submission_type,
                "return_y": "False",
                "return_eval": "True"}

        headers = { 'Content-Type':'application/json', 'authorizationToken': json.dumps({"token":os.environ.get("AWS_TOKEN"),"eval":"TEST"}), } 
        apiurl_eval=apiurl[:-1]+"eval"
        prediction = requests.post(apiurl_eval,headers=headers,data=json.dumps(post_dict))

    else:

        post_dict = {"y_pred": prediction_submission,
                "return_eval": "True",
                "submission_type": submission_type,
                "return_y": "False"}

        headers = { 'Content-Type':'application/json', 'authorizationToken': json.dumps({"token":os.environ.get("AWS_TOKEN"),"eval":"TEST"}), } 
        apiurl_eval=apiurl[:-1]+"eval"
        import requests
        prediction = requests.post(apiurl_eval,headers=headers,data=json.dumps(post_dict)) 

    # Parse the raw API response
    eval_metrics_raw = json.loads(prediction.text)
    
    # Validate API response structure
    # NOTE: Replaced 'return print(...)' with raise to prevent silent None propagation
    if not isinstance(eval_metrics_raw, dict):
        if isinstance(eval_metrics_raw, list):
            error_msg = str(eval_metrics_raw[0]) if eval_metrics_raw else "Empty list response"
            raise RuntimeError(f'Unauthorized user: {error_msg}')
        else:
            raise RuntimeError('Unauthorized user: You do not have access to submit models to, or request data from, this competition.')
    
    if "message" in eval_metrics_raw:
        raise RuntimeError(f'Unauthorized user: {eval_metrics_raw.get("message", "You do not have access to submit models to, or request data from, this competition.")}')
    
    # Extract S3 presigned URL structure separately (before normalizing eval metrics)
    s3_presigned_dict = {key: val for key, val in eval_metrics_raw.items() if key != 'eval'}
    
    if 'idempotentmodel_version' not in s3_presigned_dict:
        raise RuntimeError("Failed to get model version from API. Please check the API response.")
    
    idempotentmodel_version = s3_presigned_dict['idempotentmodel_version']
    s3_presigned_dict.pop('idempotentmodel_version')
    
    # Normalize eval metrics using helper function
    # This returns (public_eval_dict, private_eval_dict) regardless of API response shape
    eval_metrics, eval_metrics_private = _normalize_eval_payload(eval_metrics_raw)
    
    # Check if we got any valid metrics
    if not eval_metrics and not eval_metrics_private:
        print("---------------------------------------------------------------")
        print("--- WARNING: No evaluation metrics returned from API ---")
        print("Proceeding with empty metrics. Model will be submitted without eval data.")
        print("---------------------------------------------------------------")


    #upload preprocessor (1s for small upload vs 21 for 306 mbs)
    putfilekeys=list(s3_presigned_dict['put'].keys())
    
    # Find preprocessor upload key using explicit pattern matching
    # Prefer keys containing 'preprocessor_v' or 'preprocessor' ending in '.zip'
    preprocessor_key = None
    for key in putfilekeys:
        if 'preprocessor_v' in key and key.endswith('.zip'):
            preprocessor_key = key
            break
        elif 'preprocessor' in key and key.endswith('.zip'):
            preprocessor_key = key
    
    if preprocessor_key is None and preprocessor is not None:
        # Fallback to original logic if no explicit match
        modelputfiles = [s for s in putfilekeys if str("zip") in s]
        if modelputfiles:
            preprocessor_key = modelputfiles[0]
    
    if preprocessor is not None:
        if preprocessor_key is None:
            raise RuntimeError("Failed to find preprocessor upload URL in presigned URLs")
        
        filedownload_dict = ast.literal_eval(s3_presigned_dict['put'][preprocessor_key])
        
        with open(preprocessor, 'rb') as f:
            files = {'file': (preprocessor, f)}
            http_response = requests.post(filedownload_dict['url'], data=filedownload_dict['fields'], files=files)
            
            # Validate upload response status
            if http_response.status_code not in [200, 204]:
                raise RuntimeError(
                    f"Preprocessor upload failed with status {http_response.status_code}: {http_response.text}"
                )

    putfilekeys=list(s3_presigned_dict['put'].keys())
    modelputfiles = [s for s in putfilekeys if str("onnx") in s]

    fileputlistofdicts=[]
    for i in modelputfiles:
      filedownload_dict=ast.literal_eval(s3_presigned_dict ['put'][i])
      fileputlistofdicts.append(filedownload_dict)


    if not (model_filepath == None or isinstance(model_filepath, str)): 

        if isinstance(model_filepath, onnx.ModelProto):
            onnx_model = model_filepath
        else:
            print("Transform model object to onnx.")
            try:
                import torch
                if isinstance(model_filepath, torch.nn.Module) and model_input==None:
                    onnx_model = model_to_onnx(model_filepath, model_input=model_input)
            except:
                onnx_model = model_to_onnx(model_filepath)
                pass


        temp_prep=tmp.mkdtemp()
        model_filepath = temp_prep+"/model.onnx"
        with open(model_filepath, "wb") as f:
            f.write(onnx_model.SerializeToString())

        load_onnx_from_path = False
    else:
        load_onnx_from_path = True


    if model_filepath is not None:
        with open(model_filepath, 'rb') as f:
          files = {'file': (model_filepath, f)}
          http_response = requests.post(fileputlistofdicts[1]['url'], data=fileputlistofdicts[1]['fields'], files=files)


    putfilekeys=list(s3_presigned_dict['put'].keys())
    modelputfiles = [s for s in putfilekeys if str("reproducibility") in s]

    fileputlistofdicts=[]
    for i in modelputfiles:
      filedownload_dict=ast.literal_eval(s3_presigned_dict ['put'][i])
      fileputlistofdicts.append(filedownload_dict)

    if reproducibility_env_filepath:
        with open(reproducibility_env_filepath, 'rb') as f:
          files = {'file': (reproducibility_env_filepath, f)}
          http_response = requests.post(fileputlistofdicts[0]['url'], data=fileputlistofdicts[0]['fields'], files=files)

    # Model metadata upload
    if model_filepath:
        putfilekeys=list(s3_presigned_dict['put'].keys())
        modelputfiles = [s for s in putfilekeys if str("model_metadata") in s]

        fileputlistofdicts=[]
        for i in modelputfiles:
            filedownload_dict=ast.literal_eval(s3_presigned_dict ['put'][i])
            fileputlistofdicts.append(filedownload_dict)

        if load_onnx_from_path:
            onnx_model = onnx.load(model_filepath)

        meta_dict = _get_metadata(onnx_model)
        model_metadata = {
            "model_config": meta_dict["model_config"],
            "ml_framework": meta_dict["ml_framework"],
            "model_type": meta_dict["model_type"]
        }

        temp = tmp.mkdtemp()
        model_metadata_path = temp + "/" + 'model_metadata.json'
        with open(model_metadata_path, 'w') as outfile:
            json.dump(model_metadata, outfile)

        with open(model_metadata_path, 'rb') as f:
            files = {'file': (model_metadata_path, f)}
            http_response = requests.post(fileputlistofdicts[0]['url'], data=fileputlistofdicts[0]['fields'], files=files)


    # Upload model metrics and metadata {{{
    if load_onnx_from_path:
        modelleaderboarddata = _update_leaderboard_public(
            model_filepath, eval_metrics, s3_presigned_dict, custom_metadata)

        # Upload model metrics and metadata {{{
        modelleaderboarddata_private = _update_leaderboard_public(
            model_filepath, eval_metrics_private, s3_presigned_dict, custom_metadata, private=True)
    else:
        modelleaderboarddata = _update_leaderboard_public(
            None, eval_metrics, s3_presigned_dict, custom_metadata, onnx_model=onnx_model)

        # Upload model metrics and metadata {{{
        modelleaderboarddata_private = _update_leaderboard_public(
            None, eval_metrics_private, s3_presigned_dict, custom_metadata, private=True, onnx_model=onnx_model)


    model_versions = [os.path.splitext(f)[0].split("_")[-1][1:] for f in s3_presigned_dict['put'].keys()]

    model_versions = filter(lambda v: v.isnumeric(), model_versions)
    model_versions = list(map(int, model_versions))
    model_version=model_versions[0]


    if load_onnx_from_path:
        if model_filepath is not None:

            upload_model_dict(model_filepath, s3_presigned_dict, bucket, model_id, model_version)

            upload_model_graph(model_filepath, s3_presigned_dict, bucket, model_id, model_version)

        else:

            upload_model_dict(model_filepath, s3_presigned_dict, bucket, model_id, model_version, placeholder=True) 
    else:

            upload_model_dict(None, s3_presigned_dict, bucket, model_id, model_version, onnx_model=onnx_model)

            upload_model_graph(None, s3_presigned_dict, bucket, model_id, model_version, onnx_model=onnx_model)

    modelpath=model_filepath

    def dict_clean(items):
      result = {}
      for key, value in items:
          if value is None:
              value = '0'
          result[key] = value
      return result

    if isinstance(modelleaderboarddata, Exception):
      raise err

    else:
      dict_str = json.dumps(modelleaderboarddata)
    #convert None type values to string
      modelleaderboarddata_cleaned = json.loads(dict_str, object_pairs_hook=dict_clean)


    if isinstance(modelleaderboarddata_private, Exception):
      raise err
    else:
      dict_str = json.dumps(modelleaderboarddata_private)
    #convert None type values to string
      modelleaderboarddata_private_cleaned = json.loads(dict_str, object_pairs_hook=dict_clean)

    # Update model version and sample data {{{
    #data_types = None
    #data_columns = None
    #if sample_data is not None and isinstance(sample_data, pd.DataFrame):
    #    data_types = list(sample_data.dtypes.values.astype(str))
    #    data_columns = list(sample_data.columns)

    #kwargs = {
    #    "delete": "FALSE",
    #    "versionupdateget": "FALSE",
    #    "versionupdateput": "TRUE",
    #    "version": model_version,
    #    "input_feature_dtypes": data_types,
    #    "input_feature_names": data_columns,
    #}
    #response, error = run_function_on_lambda(apiurl, aws_token, **kwargs)
    #if error is not None:
    #    raise error
    # }}}

    if input_dict == None:
        modelsubmissiontags=input("Insert search tags to help users find your model (optional): ")
        modelsubmissiondescription=input("Provide any useful notes about your model (optional): ")
    else:
        modelsubmissiontags = input_dict["tags"]
        modelsubmissiondescription = input_dict["description"] 


    if submission_type=="competition":
        experimenttruefalse="FALSE"
    else:
        experimenttruefalse="TRUE"

    #Update competition or experiment data
    bodydata = {"apiurl": apiurl,
                "submissions": model_version,
                  "contributoruniquenames":os.environ.get('username'),
                "versionupdateputsubmit":"TRUE",
                 "experiment":experimenttruefalse
                                }

    # Get the response
    headers_with_authentication = {'Content-Type': 'application/json', 'authorizationToken': os.environ.get("AWS_TOKEN"), 'Access-Control-Allow-Headers':
                                    'Content-Type,X-Amz-Date,authorizationToken,Access-Control-Allow-Origin,X-Api-Key,X-Amz-Security-Token,Authorization', 'Access-Control-Allow-Origin': '*'}
    # competitiondata lambda function invoked through below url to update model submissions and contributors
    requests.post("https://o35jwfakca.execute-api.us-east-1.amazonaws.com/dev/modeldata",
                  json=bodydata, headers=headers_with_authentication)


    if modelpath is not None:

        # get model summary from onnx
        if load_onnx_from_path:
            onnx_model = onnx.load(modelpath)
        meta_dict = _get_metadata(onnx_model)

        if meta_dict['ml_framework'] == 'keras':

            inspect_pd = _model_summary(meta_dict)
            model_graph = ""

        if meta_dict['ml_framework'] == 'pytorch':

            inspect_pd = _model_summary(meta_dict)
            model_graph = ""
            
        elif meta_dict['ml_framework'] in ['sklearn', 'xgboost']:
            
            # Normalize model_config to dict (handles None, dict, or string)
            model_config = _normalize_model_config(
                meta_dict.get("model_config"), 
                meta_dict.get('model_type')
            )
            
            # Build parameter inspection DataFrame
            inspect_pd = _build_sklearn_param_dataframe(
                meta_dict['model_type'], 
                model_config
            )

            model_graph = ''

        elif meta_dict['ml_framework'] in ['pyspark']:
            
            # Normalize model_config to dict (handles None, dict, or string)
            model_config_temp = _normalize_model_config(
                meta_dict.get("model_config"), 
                meta_dict.get('model_type')
            )

            try:
                model_class = pyspark_model_from_string(meta_dict['model_type'])
                default = model_class()

                # get model config dict from pyspark model object
                default_config_temp = {}
                for key, value in default.extractParamMap().items():
                    default_config_temp[key.name] = value
                
                # Sort the keys so default and model config key matches each other
                model_config = dict(sorted(model_config_temp.items()))
                default_config = dict(sorted(default_config_temp.items()))
                
                model_configkeys = model_config.keys()
                model_configvalues = model_config.values()
                default_config = default_config.values()
            except:
                model_class = str(pyspark_model_from_string(meta_dict['model_type']))
                if model_class.find("Voting") > 0:
                    default_config = ["No data available"]
                    model_configkeys = ["No data available"]
                    model_configvalues = ["No data available"]
                else:
                    # Fallback for other exceptions
                    default_config = []
                    model_configkeys = []
                    model_configvalues = []

            inspect_pd = pd.DataFrame({'param_name': model_configkeys,
                                    'default_value': default_config,
                                    'param_value': model_configvalues})
            model_graph = ""
    else: 

        inspect_pd = pd.DataFrame()
        model_graph = ''
        
        
    keys_to_extract = [ "accuracy", "f1_score", "precision", "recall", "mse", "rmse", "mae", "r2"]

    # Safely extract metric subsets using helper function
    eval_metrics_subset = _subset_numeric(eval_metrics, keys_to_extract)
    eval_metrics_private_subset = _subset_numeric(eval_metrics_private, keys_to_extract)

    # Keep only numeric values (already done by _subset_numeric, but kept for backward compatibility)
    eval_metrics_subset_nonulls = {key: value for key, value in eval_metrics_subset.items() if isinstance(value, (int, float))}
    eval_metrics_private_subset_nonulls = {key: value for key, value in eval_metrics_private_subset.items() if isinstance(value, (int, float))}

                              
    #Update model architecture data
    bodydatamodels = {
                "apiurl": apiurl,
                "modelsummary":json.dumps(inspect_pd.to_json()),
                "model_graph": model_graph,
                "Private":"FALSE",
                "modelsubmissiondescription": modelsubmissiondescription,
                "modelsubmissiontags":modelsubmissiontags,
                  "eval_metrics":json.dumps(eval_metrics_subset_nonulls),
                  "eval_metrics_private":json.dumps(eval_metrics_private_subset_nonulls),
                  "submission_type": submission_type

                  }

    bodydatamodels.update(modelleaderboarddata_cleaned)
    bodydatamodels.update(modelleaderboarddata_private_cleaned)

    d = bodydatamodels

    keys_values = d.items()


    bodydatamodels_allstrings = {str(key): str(value) for key, value in keys_values}



    # Get the response
    headers_with_authentication = {'Content-Type': 'application/json', 'authorizationToken': os.environ.get("AWS_TOKEN"), 'Access-Control-Allow-Headers':
                                    'Content-Type,X-Amz-Date,authorizationToken,Access-Control-Allow-Origin,X-Api-Key,X-Amz-Security-Token,Authorization', 'Access-Control-Allow-Origin': '*'}
    # competitiondata lambda function invoked through below url to update model submissions and contributors
    response=requests.post("https://eeqq8zuo9j.execute-api.us-east-1.amazonaws.com/dev/modeldata",
                  json=bodydatamodels_allstrings, headers=headers_with_authentication)
    
    if str(response.status_code)=="200":
        code_comp_result="To submit code used to create this model or to view current leaderboard navigate to Model Playground: \n\n https://www.modelshare.ai/detail/model:"+response.text.split(":")[1]  
    else:
        code_comp_result="" #TODO: reponse 403 indicates that user needs to reset credentials.  Need to add a creds check to top of function.

    # NOTE: Always return tuple (version, url) to prevent None propagation
    # Print output is handled separately to maintain backward compatibility
    model_page_url = "https://www.modelshare.ai/detail/model:"+response.text.split(":")[1]
    
    if print_output:
        print("\nYour model has been submitted as model version "+str(model_version)+ "\n\n"+code_comp_result)
    
    return str(model_version), model_page_url

def update_runtime_model(apiurl, model_version=None, submission_type="competition"):
    """
    apiurl: string of API URL that the user wishes to edit
    new_model_version: string of model version number (from leaderboard) to replace original model 
    """
    import os 
    if os.environ.get("cloud_location") is not None:
        cloudlocation=os.environ.get("cloud_location")
    else:
        cloudlocation="not set"
    if "model_share"==cloudlocation:
            def nonecheck(objinput=""):
                if objinput==None:
                  objinput="None"
                else:
                  objinput="'/tmp/"+objinput+"'"
                return objinput

            runtimemodstring="update_runtime_model('"+apiurl+"',"+str(model_version)+",submission_type='"+str(submission_type)+"')"
            import base64
            import requests
            import json

            api_url = "https://z4kvag4sxdnv2mvs2b6c4thzj40bxnuw.lambda-url.us-east-2.on.aws/"

            data = json.dumps({"code": """from aimodelshare.model import update_runtime_model;"""+runtimemodstring, "zipfilename": "","username":os.environ.get("username"), "password":os.environ.get("password"),"token":os.environ.get("JWT_AUTHORIZATION_TOKEN"),"s3keyid":"xrjpv1i7xe"})

            headers = {"Content-Type": "application/json"}

            response = requests.request("POST", api_url, headers = headers, data=data)
            # Print response
            result=json.loads(response.text)

            for i in json.loads(result['body']):
                print(i)
    
    else:
        # Confirm that creds are loaded, print warning if not
        if all(["AWS_ACCESS_KEY_ID_AIMS" in os.environ, 
                "AWS_SECRET_ACCESS_KEY_AIMS" in os.environ,
                "AWS_REGION_AIMS" in os.environ,
              "username" in os.environ, 
              "password" in os.environ]):
            pass
        else:
            return print("'Update Runtime Model' unsuccessful. Please provide credentials with set_credentials().")

        # Create user session
        aws_client_and_resource=get_aws_client(aws_key=os.environ.get('AWS_ACCESS_KEY_ID_AIMS'), 
                                  aws_secret=os.environ.get('AWS_SECRET_ACCESS_KEY_AIMS'), 
                                  aws_region=os.environ.get('AWS_REGION_AIMS'))
        aws_client = aws_client_and_resource['client']
        
        user_sess = boto3.session.Session(aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID_AIMS'), 
                                          aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY_AIMS'), 
                                          region_name=os.environ.get('AWS_REGION_AIMS'))
        
        s3 = user_sess.resource('s3')
        model_version=str(model_version)
        # Get bucket and model_id for user based on apiurl {{{
        response, error = run_function_on_lambda(
            apiurl, **{"delete": "FALSE", "versionupdateget": "TRUE"}
        )
        if error is not None:
            raise error
        import json
        _, api_bucket, model_id = json.loads(response.content.decode("utf-8"))
        # }}}

        try:
            leaderboard = get_leaderboard(apiurl=apiurl, submission_type=submission_type)

            columns = leaderboard.columns
            leaderboardversion=leaderboard[leaderboard['version']==int(model_version)]
            leaderboardversion=leaderboardversion.dropna(axis=1)

            metric_names_subset=list(columns[0:4])
            leaderboardversiondict=leaderboardversion.loc[:,metric_names_subset].to_dict('records')[0]

        except Exception as err:
            raise err

        # Get file list for current bucket {{{
        model_files, err = _get_file_list(aws_client, api_bucket, model_id+"/"+submission_type)
        if err is not None:
            raise err
        # }}}

        # extract subfolder objects specific to the model id
        folder = s3.meta.client.list_objects(Bucket=api_bucket, Prefix=model_id+"/"+submission_type+"/")
        bucket = s3.Bucket(api_bucket)
        file_list = [file['Key'] for file in folder['Contents']]
        s3 = boto3.resource('s3')
        model_source_key = model_id+"/"+submission_type+"/onnx_model_v"+str(model_version)+".onnx"
        preprocesor_source_key = model_id+"/"+submission_type+"/preprocessor_v"+str(model_version)+".zip"
        model_copy_source = {
              'Bucket': api_bucket,
              'Key': model_source_key
            }
        preprocessor_copy_source = {
              'Bucket': api_bucket,
              'Key': preprocesor_source_key
          }
        # Sending correct model metrics to front end 
        bodydatamodelmetrics={"apiurl":apiurl,
                              "versionupdateput":"TRUE",
                              "verified_metrics":"TRUE",
                              "eval_metrics":json.dumps(leaderboardversiondict)}
        import requests
        headers = { 'Content-Type':'application/json', 'authorizationToken': os.environ.get("AWS_TOKEN"), } 
        prediction = requests.post("https://bhrdesksak.execute-api.us-east-1.amazonaws.com/dev/modeldata",headers=headers,data=json.dumps(bodydatamodelmetrics)) 

        # overwrite runtime_model.onnx file & runtime_preprocessor.zip files: 
        if (model_source_key in file_list) & (preprocesor_source_key in file_list):
            response = bucket.copy(model_copy_source, model_id+"/"+'runtime_model.onnx')
            response = bucket.copy(preprocessor_copy_source, model_id+"/"+'runtime_preprocessor.zip')
            return print('Runtime model & preprocessor for api: '+apiurl+" updated to model version "+model_version+".\n\nModel metrics are now updated and verified for this model playground.")
        else:
            # the file resource to be the new runtime_model is not available
            return print('New Runtime Model version ' + model_version + ' not found.')
    

def _extract_model_metadata(model, eval_metrics=None):
    # Getting the model metadata {{{
    graph = model.graph

    if eval_metrics is not None:
        metadata = eval_metrics
    else:
        metadata = dict()

    metadata["num_nodes"] = len(graph.node)
    metadata["depth_test"] = len(graph.initializer)
    metadata["num_params"] = sum(np.product(node.dims) for node in graph.initializer)

    # layers = ""
    # for node in graph.node:
    #     # consider type and get node attributes (??)
    #     layers += (
    #         node.op_type
    #         + "x".join(str(d.ints) for d in node.attribute if hasattr(d, 'ints'))
    #     )
    metadata["layers"] = "; ".join(node.op_type for node in graph.node)

    inputs = ""
    for inp in graph.input:
        dims = []
        for d in inp.type.tensor_type.shape.dim:
            if d.dim_param != "":
                dims.append(d.dim_param)
            else:
                dims.append(str(d.dim_value))

        metadata["input_shape"] = dims
        inputs += f"{inp.name} ({'x'.join(dims)})"
    metadata["inputs"] = inputs

    outputs = ""
    for out in graph.output:
        dims = []
        for d in out.type.tensor_type.shape.dim:
            if d.dim_param != "":
                dims.append(d.dim_param)
            else:
                dims.append(str(d.dim_value))

        outputs += f"{out.name} ({'x'.join(dims)})"
    metadata["outputs"] = outputs
    # }}}

    return metadata

__all__ = [
    submit_model,
    _extract_model_metadata,
    update_runtime_model
]
