# Justice & Equity Challenge Example

This example demonstrates how to use the Moral Compass system with multiple metrics to track progress on fairness-focused AI challenges.

## Overview

The dynamic metric support allows you to:
- Track multiple performance metrics (accuracy, fairness, robustness, etc.)
- Designate a primary metric for leaderboard scoring
- Track task and question progress
- Automatically compute moral compass scores

## Moral Compass Score Formula

```
moralCompassScore = primaryMetricValue × ((tasksCompleted + questionsCorrect) / (totalTasks + totalQuestions))
```

This formula combines:
- **Performance**: The value of your primary metric (e.g., accuracy)
- **Progress**: Your completion rate across tasks and questions

## Example 1: Basic Multi-Metric Usage

```python
from aimodelshare.moral_compass import ChallengeManager

# Create a challenge manager
manager = ChallengeManager(
    table_id="justice-equity-2024",
    username="participant_alice"
)

# Set multiple metrics
manager.set_metric("accuracy", 0.85, primary=True)  # Primary metric for scoring
manager.set_metric("demographic_parity", 0.92)
manager.set_metric("equal_opportunity", 0.88)
manager.set_metric("predictive_parity", 0.90)

# Track progress
manager.set_progress(
    tasks_completed=3,
    total_tasks=5,
    questions_correct=8,
    total_questions=10
)

# Preview local score before syncing
print(f"Local score preview: {manager.get_local_score():.4f}")
# Output: Local score preview: 0.5667
# Calculation: 0.85 × ((3 + 8) / (5 + 10)) = 0.85 × 0.7333 = 0.5667

# Sync to server
response = manager.sync()
print(f"Server moral compass score: {response['moralCompassScore']:.4f}")
```

## Example 2: API Client Direct Usage

```python
from aimodelshare.moral_compass import MoralcompassApiClient

client = MoralcompassApiClient()

# Create challenge table
client.create_table(
    table_id="fairness-benchmark-2024",
    display_name="AI Fairness Benchmark Challenge 2024"
)

# Update moral compass with multiple metrics
result = client.update_moral_compass(
    table_id="fairness-benchmark-2024",
    username="participant_bob",
    metrics={
        "accuracy": 0.87,
        "statistical_parity": 0.94,
        "calibration": 0.89,
        "equalized_odds": 0.91
    },
    primary_metric="statistical_parity",  # Choose fairness metric as primary
    tasks_completed=4,
    total_tasks=6,
    questions_correct=7,
    total_questions=9
)

print(f"Moral compass score: {result['moralCompassScore']}")
print(f"Primary metric: {result['primaryMetric']}")
```

## Example 3: Progressive Challenge Completion

```python
from aimodelshare.moral_compass import ChallengeManager

manager = ChallengeManager(
    table_id="ai-ethics-challenge",
    username="team_fairness"
)

# Stage 1: Initial model
manager.set_metric("accuracy", 0.80, primary=True)
manager.set_metric("fairness_score", 0.70)
manager.set_progress(tasks_completed=1, total_tasks=5)
response1 = manager.sync()
print(f"Stage 1 score: {response1['moralCompassScore']:.4f}")
# 0.80 × (1/5) = 0.16

# Stage 2: Improved fairness
manager.set_metric("accuracy", 0.78)  # Slight accuracy trade-off
manager.set_metric("fairness_score", 0.88)
manager.set_progress(tasks_completed=3, total_tasks=5)
response2 = manager.sync()
print(f"Stage 2 score: {response2['moralCompassScore']:.4f}")
# 0.78 × (3/5) = 0.468

# Stage 3: Final model with questions
manager.set_metric("accuracy", 0.82)
manager.set_metric("fairness_score", 0.92)
manager.set_progress(
    tasks_completed=5, 
    total_tasks=5,
    questions_correct=8,
    total_questions=10
)
response3 = manager.sync()
print(f"Stage 3 score: {response3['moralCompassScore']:.4f}")
# 0.82 × ((5 + 8) / (5 + 10)) = 0.82 × 0.8667 = 0.7107
```

## Example 4: Leaderboard Query

```python
from aimodelshare.moral_compass import MoralcompassApiClient

client = MoralcompassApiClient()

# Get leaderboard (automatically sorted by moralCompassScore)
users = list(client.iter_users("justice-equity-2024"))

print("=== Justice & Equity Challenge Leaderboard ===")
for i, user in enumerate(users[:10], 1):
    score = user.get('moralCompassScore', 0)
    metrics = user.get('metrics', {})
    primary = user.get('primaryMetric', 'N/A')
    
    print(f"{i}. {user['username']}: {score:.4f}")
    print(f"   Primary metric ({primary}): {metrics.get(primary, 0):.3f}")
    if 'tasksCompleted' in user:
        progress = (user['tasksCompleted'] + user.get('questionsCorrect', 0)) / \
                   (user.get('totalTasks', 1) + user.get('totalQuestions', 1))
        print(f"   Progress: {progress:.1%}")
    print()
```

## Example 5: Custom Metrics for Different Fairness Criteria

```python
from aimodelshare.moral_compass import ChallengeManager

# Gender fairness focus
manager = ChallengeManager("bias-detection-2024", "researcher_carol")

manager.set_metric("accuracy", 0.89)
manager.set_metric("gender_demographic_parity", 0.95, primary=True)
manager.set_metric("gender_equal_opportunity", 0.93)
manager.set_metric("gender_calibration", 0.91)
manager.set_progress(tasks_completed=4, total_tasks=4)

result = manager.sync()
print(f"Gender fairness score: {result['moralCompassScore']:.4f}")

# Multi-attribute fairness
manager2 = ChallengeManager("intersectional-fairness", "researcher_david")

manager2.set_metric("overall_accuracy", 0.86)
manager2.set_metric("race_fairness", 0.90)
manager2.set_metric("gender_fairness", 0.92)
manager2.set_metric("age_fairness", 0.88)
manager2.set_metric("intersectional_fairness", 0.85, primary=True)
manager2.set_progress(
    tasks_completed=5,
    total_tasks=5,
    questions_correct=10,
    total_questions=10
)

result2 = manager2.sync()
print(f"Intersectional fairness score: {result2['moralCompassScore']:.4f}")
# 0.85 × ((5 + 10) / (5 + 10)) = 0.85 × 1.0 = 0.85
```

## Metric Selection Guidelines

### Common Fairness Metrics

- **accuracy**: Overall model accuracy
- **demographic_parity**: Equal positive prediction rates across groups
- **equal_opportunity**: Equal true positive rates across groups
- **equalized_odds**: Equal TPR and FPR across groups
- **predictive_parity**: Equal precision across groups
- **calibration**: Predicted probabilities match actual outcomes
- **statistical_parity**: Equal selection rates across groups

### Choosing a Primary Metric

The primary metric determines the leaderboard ranking. Choose based on:
1. **Challenge goals**: Fairness-focused vs. accuracy-focused
2. **Application context**: Medical diagnosis (equal opportunity) vs. loan approval (demographic parity)
3. **Stakeholder priorities**: What matters most to affected communities

### Default Behavior

If no primary metric is specified:
- If `accuracy` exists in metrics, it becomes primary
- Otherwise, the first metric alphabetically becomes primary

## Best Practices

1. **Set meaningful progress counters**: Use tasks for major milestones and questions for knowledge checks
2. **Update incrementally**: Sync after each significant improvement to track progress
3. **Include multiple fairness metrics**: No single metric captures all aspects of fairness
4. **Document your metrics**: Add comments explaining what each metric measures
5. **Preview locally**: Use `get_local_score()` to verify calculations before syncing

## Backward Compatibility

Users created with the legacy `put_user` endpoint (using only submissionCount/totalCount) will:
- Continue to work normally
- Sort by submissionCount on leaderboards
- Appear below users with moralCompassScore > 0

## Migration Example

```python
# Legacy approach (still supported)
client.put_user("my-table", "user1", submission_count=10, total_count=100)

# New approach with metrics
client.update_moral_compass(
    table_id="my-table",
    username="user1",
    metrics={"accuracy": 0.90},
    tasks_completed=10,
    total_tasks=100
)
```

## Additional Resources

- [API Client Documentation](../aimodelshare/moral_compass/README.md)
- [DynamoDB Schema](../infra/lambda/app.py)
- [Integration Tests](../tests/test_moral_compass_client_minimal.py)
