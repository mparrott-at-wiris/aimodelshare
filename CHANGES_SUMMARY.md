# Summary of Changes to Fix Model Playground Submit Error

## Problem
The `test_playground_penguins` test was failing with:
```
TypeError: cannot unpack non-iterable NoneType object
```

This occurred because `submit_model` used `return print(...)` statements which return `None`, breaking tuple unpacking in calling code.

## Root Causes
1. Early returns using `return print(...)` produce `None` and break tuple unpacking
2. Authorization / eval error handling logic in `submit_model` returned via `print` without raising structured exceptions
3. `ModelPlayground.submit_model` unpacked without validating the returned object
4. HiddenPrints suppresses diagnostic output, masking underlying issues

## Changes Made

### 1. aimodelshare/model.py::submit_model

#### Line 729-734: Credential Check
**Before:**
```python
if all(["username" in os.environ, 
        "password" in os.environ]):
    pass
else:
    return print("'Submit Model' unsuccessful. Please provide username and password using set_credentials() function.")
```

**After:**
```python
# Confirm that creds are loaded, raise error if not
# NOTE: Replaced 'return print(...)' with raise to prevent silent None propagation
if not all(["username" in os.environ, 
            "password" in os.environ]):
    raise RuntimeError("'Submit Model' unsuccessful. Please provide username and password using set_credentials() function.")
```

#### Lines 831-851: API Response Validation
**Before:**
```python
# Validate API response structure
if not isinstance(eval_metrics_raw, dict):
    if isinstance(eval_metrics_raw, list):
        print(eval_metrics_raw[0])
    else:
        return print('Unauthorized user: You do not have access to submit models to, or request data from, this competition.')

if "message" in eval_metrics_raw:
    return print('Unauthorized user: You do not have access to submit models to, or request data from, this competition.')

# Extract S3 presigned URL structure separately (before normalizing eval metrics)
s3_presigned_dict = {key: val for key, val in eval_metrics_raw.items() if key != 'eval'}

if 'idempotentmodel_version' not in s3_presigned_dict:
    return print("Failed to get model version from API. Please check the API response.")
```

**After:**
```python
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
```

#### Lines 1217-1229: Final Return Statement
**Before:**
```python
if str(response.status_code)=="200":
    code_comp_result="To submit code used to create this model or to view current leaderboard navigate to Model Playground: \n\n https://www.modelshare.ai/detail/model:"+response.text.split(":")[1]  
else:
    code_comp_result="" #TODO: reponse 403 indicates that user needs to reset credentials.  Need to add a creds check to top of function.

if print_output:
    return print("\nYour model has been submitted as model version "+str(model_version)+ "\n\n"+code_comp_result)
else:
    return str(model_version), "https://www.modelshare.ai/detail/model:"+response.text.split(":")[1]
```

**After:**
```python
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
```

### 2. aimodelshare/playground.py::ModelPlayground.submit_model

#### Lines 1245-1283: Added Defensive Validation
**Before:**
```python
if submission_type == "competition" or submission_type == "all":
    with HiddenPrints():
        competition = Competition(self.playground_url)

        version_comp, model_page = competition.submit_model(model=model,
                                                            prediction_submission=prediction_submission,
                                                            preprocessor=preprocessor,
                                                            reproducibility_env_filepath=reproducibility_env_filepath,
                                                            custom_metadata=custom_metadata,
                                                            input_dict=input_dict,
                                                            print_output=False)

    print(f"Your model has been submitted to competition as model version {version_comp}.")

if submission_type == "experiment" or submission_type == "all":
    with HiddenPrints():
        experiment = Experiment(self.playground_url)

        version_exp, model_page = experiment.submit_model(model=model,
                                                          prediction_submission=prediction_submission,
                                                          preprocessor=preprocessor,
                                                          reproducibility_env_filepath=reproducibility_env_filepath,
                                                          custom_metadata=custom_metadata,
                                                          input_dict=input_dict,
                                                          print_output=False)

    print(f"Your model has been submitted to experiment as model version {version_exp}.")
```

**After:**
```python
if submission_type == "competition" or submission_type == "all":
    with HiddenPrints():
        competition = Competition(self.playground_url)

        comp_result = competition.submit_model(model=model,
                                               prediction_submission=prediction_submission,
                                               preprocessor=preprocessor,
                                               reproducibility_env_filepath=reproducibility_env_filepath,
                                               custom_metadata=custom_metadata,
                                               input_dict=input_dict,
                                               print_output=False)
        
        # Validate return structure before unpacking
        if not isinstance(comp_result, tuple) or len(comp_result) != 2:
            raise RuntimeError(f"Invalid return from competition.submit_model: expected (version, url) tuple, got {type(comp_result)}")
        
        version_comp, model_page = comp_result

    print(f"Your model has been submitted to competition as model version {version_comp}.")

if submission_type == "experiment" or submission_type == "all":
    with HiddenPrints():
        experiment = Experiment(self.playground_url)

        exp_result = experiment.submit_model(model=model,
                                             prediction_submission=prediction_submission,
                                             preprocessor=preprocessor,
                                             reproducibility_env_filepath=reproducibility_env_filepath,
                                             custom_metadata=custom_metadata,
                                             input_dict=input_dict,
                                             print_output=False)
        
        # Validate return structure before unpacking
        if not isinstance(exp_result, tuple) or len(exp_result) != 2:
            raise RuntimeError(f"Invalid return from experiment.submit_model: expected (version, url) tuple, got {type(exp_result)}")
        
        version_exp, model_page = exp_result

    print(f"Your model has been submitted to experiment as model version {version_exp}.")
```

## Impact

### Positive Changes
1. **Eliminates Silent Failures**: All error conditions now raise clear `RuntimeError` exceptions instead of returning `None`
2. **Consistent Return Behavior**: `submit_model` always returns `(version, url)` tuple regardless of `print_output` parameter
3. **Better Error Messages**: RuntimeError exceptions include descriptive messages about what went wrong
4. **Defensive Programming**: Playground code validates return structure before unpacking, providing clearer error messages

### Backward Compatibility
- The `print_output=True` behavior is preserved - still prints the message, but now also returns the tuple
- Error messages are similar to before but now raised as exceptions instead of printed
- Existing code that calls `submit_model` with `print_output=False` continues to work unchanged

## Verification

All changes verified by:
1. Manual code inspection
2. grep search confirming no `return print(...)` in `submit_model` function
3. Automated verification script confirming:
   - No `return print(...)` statements in `submit_model`
   - Correct final return statement present
   - 5 RuntimeError raises added
   - Both competition and experiment result validation present

## Testing Notes

The original test (`test_playground_penguins`) requires:
- Valid AWS credentials
- Active playground/API endpoints
- Network connectivity
- Full dependency installation (onnx, sklearn, seaborn, etc.)

Due to these requirements, the test cannot be run in this environment. However, the code changes are minimal, focused, and verified to be syntactically correct and logically sound.

## Remaining Work

None of the problematic `return print(...)` patterns remain in the `submit_model` function. The remaining `return print(...)` statements in the file are in the `update_runtime_model` function, which is out of scope for this PR.
