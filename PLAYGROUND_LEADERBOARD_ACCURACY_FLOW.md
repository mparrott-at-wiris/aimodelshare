# Playground Leaderboard Accuracy Flow Documentation

## Overview
This document describes how the current user's playground leaderboard accuracy is loaded and sent to update the accuracy in the moral compass API client across the moral compass apps.

## Location
The code is located in the `aimodelshare/moral_compass/apps/` directory and is repeated across 13 different app files:

### Apps with this pattern:
1. `bias_detective_ca.py` (Catalan version)
2. `bias_detective_en.py` (English version)
3. `bias_detective_es.py` (Spanish version)
4. `bias_detective_part1.py`
5. `bias_detective_part2.py`
6. `fairness_fixer.py`
7. `fairness_fixer_ca.py` (Catalan version)
8. `fairness_fixer_en.py` (English version)
9. `fairness_fixer_es.py` (Spanish version)
10. `justice_equity_upgrade.py`
11. `justice_equity_upgrade_ca.py` (Catalan version)
12. `justice_equity_upgrade_en.py` (English version)
13. `justice_equity_upgrade_es.py` (Spanish version)

## The Complete Flow

### Step 1: Fetching User's Playground Accuracy

The `fetch_user_history()` function retrieves the user's best accuracy from the playground leaderboard.

**Location Example:** `bias_detective_en.py`, lines 56-83

```python
def fetch_user_history(username, token):
    default_acc = 0.0
    default_team = "Team-Unassigned"
    try:
        # 1. Create a Competition object to connect to the original playground
        playground = Competition(ORIGINAL_PLAYGROUND_URL)
        
        # 2. Get the leaderboard data using the user's authentication token
        df = playground.get_leaderboard(token=token)
        
        # 3. Check if leaderboard data exists
        if df is None or df.empty:
            return default_acc, default_team
            
        # 4. Filter for the current user's submissions
        if "username" in df.columns and "accuracy" in df.columns:
            user_rows = df[df["username"] == username]
            
            if not user_rows.empty:
                # 5. Get the BEST (maximum) accuracy across all user's submissions
                best_acc = user_rows["accuracy"].max()
                
                # 6. Also extract the most recent team name
                if "timestamp" in user_rows.columns and "Team" in user_rows.columns:
                    try:
                        user_rows = user_rows.copy()
                        user_rows["timestamp"] = pd.to_datetime(
                            user_rows["timestamp"], errors="coerce"
                        )
                        # Sort by timestamp descending (most recent first)
                        user_rows = user_rows.sort_values("timestamp", ascending=False)
                        found_team = user_rows.iloc[0]["Team"]
                        if pd.notna(found_team) and str(found_team).strip():
                            default_team = str(found_team).strip()
                    except Exception:
                        pass
                        
                return float(best_acc), default_team
    except Exception:
        pass
    return default_acc, default_team
```

**Key Details:**
- Connects to `ORIGINAL_PLAYGROUND_URL` (https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m)
- Uses `Competition.get_leaderboard()` from aimodelshare library
- Returns the **maximum accuracy** across all user submissions (not average or latest)
- Also returns the team name from the most recent submission
- Returns default values (0.0 accuracy, "Team-Unassigned") if any errors occur

### Step 2: Initial Load - Syncing with Moral Compass API

When the app loads, `fetch_user_history()` is called in the `handle_load()` function:

**Location Example:** `bias_detective_en.py`, lines 2578-2636

```python
def handle_load(req: gr.Request):
    success, user, token = _try_session_based_auth(req)
    team = "Team-Unassigned"
    acc = 0.0
    fetched_tasks: List[str] = []

    if success and user and token:
        # 1. Fetch the user's best playground accuracy
        acc, fetched_team = fetch_user_history(user, token)
        
        # 2. Initialize the Moral Compass API client
        os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
        client = MoralcompassApiClient(
            api_base_url=DEFAULT_API_URL, auth_token=token
        )

        # ... team assignment logic ...

        # 3. Get existing completed tasks from API
        try:
            user_stats = client.get_user(table_id=TABLE_ID, username=user)
        except Exception:
            user_stats = None

        if user_stats:
            if isinstance(user_stats, dict):
                fetched_tasks = user_stats.get("completedTaskIds") or []
            else:
                fetched_tasks = getattr(
                    user_stats, "completed_task_ids", []
                ) or []

        # 4. Sync baseline moral compass record with playground accuracy
        try:
            client.update_moral_compass(
                table_id=TABLE_ID,
                username=user,
                team_name=team,
                metrics={"accuracy": acc},  # <-- Playground accuracy sent here
                tasks_completed=len(fetched_tasks),
                total_tasks=TOTAL_COURSE_TASKS,
                primary_metric="accuracy",
                completed_task_ids=fetched_tasks,
            )
            time.sleep(1.0)
        except Exception:
            pass
```

**Key Details:**
- Called when the Gradio app loads
- Fetches playground accuracy and syncs it as a baseline to the Moral Compass API
- The accuracy represents the user's best performance on the playground
- Also syncs completed task IDs and team information

### Step 3: Updating Progress - The `trigger_api_update()` Function

When a user completes a task/module, `trigger_api_update()` sends updated data to the API:

**Location Example:** `bias_detective_en.py`, lines 1752-1799

```python
def trigger_api_update(
    username, token, team_name, module_id, user_real_accuracy, task_list_state, append_task_id=None
):
    if not username or not token:
        return None, None, username, task_list_state
        
    # 1. Initialize API client
    os.environ["MORAL_COMPASS_API_BASE_URL"] = DEFAULT_API_URL
    client = MoralcompassApiClient(api_base_url=DEFAULT_API_URL, auth_token=token)

    # 2. Convert accuracy to float (this is the playground accuracy)
    acc = float(user_real_accuracy) if user_real_accuracy is not None else 0.0

    # 3. Update the completed tasks list
    old_task_list = list(task_list_state) if task_list_state else []
    new_task_list = list(old_task_list)
    if append_task_id and append_task_id not in new_task_list:
        new_task_list.append(append_task_id)
        try:
            # Sort task IDs (e.g., t1, t2, t3...)
            new_task_list.sort(
                key=lambda x: int(x[1:]) if x.startswith("t") and x[1:].isdigit() else 0
            )
        except Exception:
            pass

    # 4. Send update to Moral Compass API
    tasks_completed = len(new_task_list)
    client.update_moral_compass(
        table_id=TABLE_ID,                    # "m-mc"
        username=username,
        team_name=team_name,
        metrics={"accuracy": acc},            # <-- Playground accuracy sent here
        tasks_completed=tasks_completed,      # Number of tasks completed
        total_tasks=TOTAL_COURSE_TASKS,       # Total tasks in course (20)
        primary_metric="accuracy",            # Which metric to use for scoring
        completed_task_ids=new_task_list,     # List of completed task IDs
    )

    # 5. Calculate the Moral Compass Score locally
    # Score = accuracy × (tasks_completed / total_tasks)
    old_score_calc = acc * (len(old_task_list) / TOTAL_COURSE_TASKS)
    new_score_calc = acc * (len(new_task_list) / TOTAL_COURSE_TASKS)

    # 6. Get leaderboard data with optimistic updates for immediate UI feedback
    prev_data = get_leaderboard_data(
        client, username, team_name, old_task_list, override_score=old_score_calc
    )
    lb_data = get_leaderboard_data(
        client, username, team_name, new_task_list, override_score=new_score_calc
    )

    return prev_data, lb_data, username, new_task_list
```

**Key Details:**
- Called after each task/module completion
- The `user_real_accuracy` parameter contains the playground accuracy
- Updates both the accuracy metric AND the completed tasks list
- Calculates Moral Compass Score: `accuracy × (tasks_completed / total_tasks)`
- Returns leaderboard data for UI updates showing rank changes

### Step 4: The Moral Compass API Client - `update_moral_compass()`

The actual API call is made through the MoralcompassApiClient:

**Location:** `aimodelshare/moral_compass/api_client.py`, lines 562-618

```python
def update_moral_compass(self, table_id: str, username: str,
                       metrics: Dict[str, float], 
                       tasks_completed: int = 0,
                       total_tasks: int = 0,
                       questions_correct: int = 0,
                       total_questions: int = 0,
                       primary_metric: Optional[str] = None,
                       team_name: Optional[str] = None,
                       completed_task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Update a user's moral compass score with dynamic metrics.
    
    The server calculates the moralCompassScore as:
        moralCompassScore = primary_metric_value × (tasks_completed / total_tasks)
    
    Args:
        table_id: The table identifier
        username: The username
        metrics: Dictionary of metric_name -> numeric_value
                 e.g., {"accuracy": 0.85}
        tasks_completed: Number of tasks completed (default: 0)
        total_tasks: Total number of tasks (default: 0)
        questions_correct: Number of questions answered correctly (default: 0)
        total_questions: Total number of questions (default: 0)
        primary_metric: Optional primary metric name (defaults to 'accuracy' or first sorted key)
        team_name: Optional team name for the user
        completed_task_ids: Optional list of completed task IDs (e.g., ['t1', 't2'])
        
    Returns:
        Dict containing moralCompassScore and other fields
    """
    payload = {
        "metrics": metrics,
        "tasksCompleted": tasks_completed,
        "totalTasks": total_tasks,
        "questionsCorrect": questions_correct,
        "totalQuestions": total_questions
    }
    
    if primary_metric is not None:
        payload["primaryMetric"] = primary_metric
    
    if team_name is not None:
        payload["teamName"] = team_name
    
    if completed_task_ids is not None:
        payload["completedTaskIds"] = completed_task_ids
    
    # Make PUT request to /tables/{table_id}/users/{username}/moral-compass
    response = self._request("PUT", f"/tables/{table_id}/users/{username}/moral-compass", json=payload)
    return response.json()
```

**Key Details:**
- Makes a PUT request to the Moral Compass API
- Endpoint: `/tables/{table_id}/users/{username}/moral-compass`
- The server calculates: `moralCompassScore = primary_metric_value × (tasks_completed / total_tasks)`
- In all apps, `primary_metric` is set to "accuracy" (the playground accuracy)
- Returns the calculated moral compass score from the server

## Configuration Constants

All apps use these constants:
```python
DEFAULT_API_URL = "https://b22q73wp50.execute-api.us-east-1.amazonaws.com/dev"
ORIGINAL_PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"
TABLE_ID = "m-mc"
TOTAL_COURSE_TASKS = 20  # Score calculated against full course
```

## Score Calculation Formula

The Moral Compass Score is calculated as:

```
Moral Compass Score = Playground Accuracy × (Tasks Completed / Total Tasks)
```

For example:
- If a user has 85% accuracy on the playground (0.85)
- And they've completed 10 out of 20 tasks
- Their Moral Compass Score = 0.85 × (10/20) = 0.425

## Data Flow Summary

```
1. User submits to playground → Accuracy recorded in playground leaderboard
                                                    ↓
2. User opens moral compass app → fetch_user_history() retrieves best playground accuracy
                                                    ↓
3. On app load → Initial sync via update_moral_compass() with baseline accuracy
                                                    ↓
4. User completes a task → trigger_api_update() sends:
                           - Playground accuracy (unchanged)
                           - Updated completed tasks list
                           - Calculates new Moral Compass Score
                                                    ↓
5. Server stores and returns → moralCompassScore for leaderboard display
```

## Code Repetition

The exact same code pattern appears in **13 different app files**:
- 3 "Bias Detective" variants (CA, EN, ES) + 2 parts
- 4 "Fairness Fixer" variants (base + CA, EN, ES)
- 4 "Justice Equity Upgrade" variants (base + CA, EN, ES)

Each file contains identical implementations of:
- `fetch_user_history()` - Retrieves playground accuracy
- `trigger_api_update()` - Sends updates to API
- `get_leaderboard_data()` - Retrieves and formats leaderboard data
- `handle_load()` - Initial app load and sync

The only differences between variants are:
- Language-specific text content in the modules
- Localized strings and translations

This represents a significant amount of code duplication that could potentially be refactored into a shared module or utility library.

## Dependencies

The flow relies on these key libraries:
- `aimodelshare.playground.Competition` - For accessing playground leaderboards
- `aimodelshare.moral_compass.MoralcompassApiClient` - For API interactions
- `aimodelshare.aws.get_token_from_session` - For authentication
- `pandas` - For DataFrame operations on leaderboard data
- `gradio` - For the web UI framework
