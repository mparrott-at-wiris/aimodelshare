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

# Moral Compass: Dynamic Metric Support for AI Ethics Challenges

The Moral Compass system now supports tracking multiple performance metrics for fairness-focused AI challenges. Track accuracy, demographic parity, equal opportunity, and other fairness metrics simultaneously.

## Quick Start with Multi-Metric Tracking

```python
from aimodelshare.moral_compass import ChallengeManager

# Create a challenge manager
manager = ChallengeManager(
    table_id="fairness-challenge-2024",
    username="your_username"
)

# Track multiple metrics
manager.set_metric("accuracy", 0.85, primary=True)
manager.set_metric("demographic_parity", 0.92)
manager.set_metric("equal_opportunity", 0.88)

# Track progress
manager.set_progress(tasks_completed=3, total_tasks=5)

# Sync to leaderboard
result = manager.sync()
print(f"Moral compass score: {result['moralCompassScore']:.4f}")
```

## Moral Compass Score Formula

```
moralCompassScore = primaryMetricValue × ((tasksCompleted + questionsCorrect) / (totalTasks + totalQuestions))
```

This combines:
- **Performance**: Your primary metric value (e.g., fairness score)
- **Progress**: Your completion rate across tasks and questions

## Features

- **Multiple Metrics**: Track accuracy, fairness, robustness, and custom metrics
- **Primary Metric Selection**: Choose which metric drives leaderboard ranking
- **Progress Tracking**: Monitor task and question completion
- **Automatic Scoring**: Server-side computation of moral compass scores
- **Leaderboard Sorting**: Automatic ranking by moral compass score
- **Backward Compatible**: Existing users without metrics continue to work

## Example: Justice & Equity Challenge

See [Justice & Equity Challenge Example](docs/justice_equity_challenge_example.md) for detailed examples including:
- Multi-metric fairness tracking
- Progressive challenge completion
- Leaderboard queries
- Custom fairness criteria

## API Methods

### ChallengeManager

```python
from aimodelshare.moral_compass import ChallengeManager

manager = ChallengeManager(table_id="my-table", username="user1")

# Set metrics
manager.set_metric("accuracy", 0.90, primary=True)
manager.set_metric("fairness", 0.95)

# Set progress
manager.set_progress(tasks_completed=4, total_tasks=5)

# Preview score locally
score = manager.get_local_score()

# Sync to server
result = manager.sync()
```

### API Client

```python
from aimodelshare.moral_compass import MoralcompassApiClient

client = MoralcompassApiClient()

# Update moral compass with metrics
result = client.update_moral_compass(
    table_id="my-table",
    username="user1",
    metrics={"accuracy": 0.90, "fairness": 0.95},
    primary_metric="fairness",
    tasks_completed=4,
    total_tasks=5
)
```

## Documentation

- [Full API Documentation](aimodelshare/moral_compass/README.md)
- [Justice & Equity Challenge Examples](docs/justice_equity_challenge_example.md)
- [Integration Tests](tests/test_moral_compass_client_minimal.py)
