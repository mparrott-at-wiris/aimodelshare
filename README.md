<p align="center"><img width="40%" src="docs/aimodshare_banner.jpg" /></p> 

### The mission of the AI Model Share Platform is to provide a trusted non profit repository for machine learning model prediction APIs (python library + integrated website at modelshare.org).  A beta version of the platform is currently being used by Columbia University students, faculty, and staff to test and improve platform functionality.

### In a matter of seconds, data scientists can launch a model into this infrastructure and end-users the world over will be able to engage their machine learning models.

* ***Launch machine learning models into scalable production ready prediction REST APIs using a single Python function.*** 

* ***Details about each model, how to use the model's API, and the model's author(s) are deployed simultaneously into a searchable website at modelshare.org.*** 

* ***Deployed models receive an individual Model Playground listing information about all deployed models. Each of these pages includes a fully functional prediction dashboard that allows end-users to input text, tabular, or image data and receive live predictions.*** 

* ***Moreover, users can build on model playgrounds by 1) creating ML model competitions, 2) uploading Jupyter notebooks to share code, 3) sharing model architectures and 4) sharing data... with all shared artifacts automatically creating a data science user portfolio.*** 

# Use aimodelshare Python library to deploy your model, create a new ML competition, and more.
* [Tutorials for deploying models](https://www.modelshare.org/search/deploy?search=ALL&problemdomain=ALL&gettingstartedguide=TRUE&pythonlibrariesused=ALL&tags=ALL&pageNum=1).

# Find model playground web-dashboards to generate predictions now.
* [View deployed models and generate predictions at modelshare.org](https://www.modelshare.org)

# Installation

## Install using PyPi 

```
pip install aimodelshare
```

## Install on Anaconda


#### Conda/Mamba Install ( For Mac and Linux Users Only , Windows Users should use pip method ) : 

Make sure you have conda version >=4.9 

You can check your conda version with:

```
conda --version
```

To update conda use: 

```
conda update conda 
```

Installing `aimodelshare` from the `conda-forge` channel can be achieved by adding `conda-forge` to your channels with:

```
conda config --add channels conda-forge
conda config --set channel_priority strict
```

Once the `conda-forge` channel has been enabled, `aimodelshare` can be installed with `conda`:

```
conda install aimodelshare
```

or with `mamba`:

```
mamba install aimodelshare
```

# moral_compass Client Library

The `moral_compass` package provides a production-ready Python client for interacting with the aimodelshare REST API. It includes auto-discovery of the API base URL, HTTP retries, typed dataclasses, and pagination helpers.

## Features

- **Auto-discovery**: Automatically finds API base URL from environment variables, cached Terraform outputs, or direct Terraform commands
- **Retries**: Built-in retry logic for transient failures (500, 502, 503, 504 errors)
- **Type Safety**: Typed dataclasses for API responses (`MoralcompassTableMeta`, `MoralcompassUserStats`)
- **Pagination**: Helper methods to iterate over all tables and users
- **Error Handling**: Structured exceptions (`NotFoundError`, `ServerError`, `ApiClientError`)

## Installation

The `moral_compass` client is included in this repository. Install in editable mode for development:

```bash
pip install -e .
```

Or install specific dependencies:

```bash
pip install requests urllib3
```

## Usage

### Basic Example

```python
from moral_compass import MoralcompassApiClient

# Create client with auto-discovery of API URL
client = MoralcompassApiClient()

# Check API health
health = client.health()
print(health)

# Create a table
response = client.create_table("my-table", "My Table")

# Get table metadata
table = client.get_table("my-table")
print(f"Table: {table.table_id}, Users: {table.user_count}")

# Create/update a user
client.put_user("my-table", "john", submission_count=5, total_count=10)

# Get user stats
user = client.get_user("my-table", "john")
print(f"User: {user.username}, Submissions: {user.submission_count}")
```

### Pagination

```python
# Iterate over all tables
for table in client.iter_tables():
    print(f"Table: {table.table_id}")

# Iterate over all users in a table
for user in client.iter_users("my-table"):
    print(f"User: {user.username}, Count: {user.submission_count}")
```

### Error Handling

```python
from moral_compass import NotFoundError

try:
    table = client.get_table("nonexistent")
except NotFoundError:
    print("Table not found")
```

## Configuration

The client auto-discovers the API base URL from these sources (in order):

1. **Environment variable** `MORAL_COMPASS_API_BASE_URL`
2. **Environment variable** `AIMODELSHARE_API_BASE_URL` (backward compatibility)
3. **Cached file** `infra/terraform_outputs.json` (written by CI/CD)
4. **Terraform command** `terraform output -raw api_base_url` (if Terraform state is accessible)

### Setting the API URL Manually

```bash
export MORAL_COMPASS_API_BASE_URL="https://your-api.execute-api.us-east-1.amazonaws.com/dev"
```

Or pass it directly when creating the client:

```python
client = MoralcompassApiClient(base_url="https://your-api.example.com")
```

## Running Integration Tests

Integration tests are marked with `@pytest.mark.integration` and require a live API:

```bash
# Run integration tests
pytest -m integration tests/test_moral_compass_client_minimal.py

# Skip integration tests
pytest -m "not integration"
```

## CI/CD Integration

The GitHub Actions workflow automatically:
1. Caches Terraform outputs to `infra/terraform_outputs.json`
2. Exports `MORAL_COMPASS_API_BASE_URL` to the environment
3. Installs the client in editable mode
4. Runs integration tests against the deployed API

See `.github/workflows/deploy-infra.yml` for details.
