#!/usr/bin/env python3
"""
Demonstration of Moral Compass Dynamic Metric Support

This script demonstrates the new multi-metric tracking functionality
without requiring a deployed API (uses mock client for demonstration).

Run: python scripts/demo_moral_compass_metrics.py
"""

from decimal import Decimal


class MockApiClient:
    """Mock API client for demonstration"""
    
    def update_moral_compass(self, **kwargs):
        """Simulate server response"""
        metrics = kwargs.get('metrics', {})
        primary_metric = kwargs.get('primary_metric')
        
        # Determine primary metric (server logic)
        if primary_metric is None:
            if 'accuracy' in metrics:
                primary_metric = 'accuracy'
            else:
                primary_metric = sorted(metrics.keys())[0]
        
        primary_value = metrics[primary_metric]
        
        # Calculate score
        tc = kwargs.get('tasks_completed', 0)
        tt = kwargs.get('total_tasks', 0)
        qc = kwargs.get('questions_correct', 0)
        qt = kwargs.get('total_questions', 0)
        
        denom = tt + qt
        if denom == 0:
            score = 0.0
        else:
            score = primary_value * ((tc + qc) / denom)
        
        return {
            'username': kwargs.get('username'),
            'metrics': metrics,
            'primaryMetric': primary_metric,
            'moralCompassScore': score,
            'tasksCompleted': tc,
            'totalTasks': tt,
            'questionsCorrect': qc,
            'totalQuestions': qt,
            'message': 'Moral compass data updated successfully',
            'createdNew': False
        }


def print_separator():
    print("\n" + "=" * 70 + "\n")


def demo_basic_usage():
    """Demonstrate basic single-metric usage"""
    print("DEMO 1: Basic Single Metric")
    print("-" * 70)
    
    from aimodelshare.moral_compass.challenge import ChallengeManager
    
    manager = ChallengeManager(
        table_id="demo-challenge",
        username="alice",
        api_client=MockApiClient()
    )
    
    # Set accuracy metric
    manager.set_metric("accuracy", 0.85, primary=True)
    manager.set_progress(tasks_completed=5, total_tasks=10)
    
    # Preview local score
    local_score = manager.get_local_score()
    print(f"Metrics: {manager.metrics}")
    print(f"Progress: {manager.tasks_completed}/{manager.total_tasks} tasks")
    print(f"Local score preview: {local_score:.4f}")
    print(f"Formula: 0.85 × (5/10) = {0.85 * (5/10):.4f}")
    
    # Sync to server
    result = manager.sync()
    print(f"\nServer response:")
    print(f"  moralCompassScore: {result['moralCompassScore']:.4f}")
    print(f"  primaryMetric: {result['primaryMetric']}")


def demo_multi_metric():
    """Demonstrate multi-metric tracking"""
    print("DEMO 2: Multiple Fairness Metrics")
    print("-" * 70)
    
    from aimodelshare.moral_compass.challenge import ChallengeManager
    
    manager = ChallengeManager(
        table_id="fairness-challenge",
        username="bob",
        api_client=MockApiClient()
    )
    
    # Set multiple metrics
    manager.set_metric("accuracy", 0.87)
    manager.set_metric("demographic_parity", 0.94, primary=True)
    manager.set_metric("equal_opportunity", 0.88)
    manager.set_metric("predictive_parity", 0.90)
    
    manager.set_progress(
        tasks_completed=3,
        total_tasks=5,
        questions_correct=8,
        total_questions=10
    )
    
    print(f"Metrics tracked: {len(manager.metrics)}")
    for name, value in sorted(manager.metrics.items()):
        marker = "★" if name == manager.primary_metric else " "
        print(f"  {marker} {name}: {value:.2f}")
    
    print(f"\nPrimary metric: {manager.primary_metric}")
    print(f"Progress: {manager.tasks_completed + manager.questions_correct}/{manager.total_tasks + manager.total_questions}")
    
    local_score = manager.get_local_score()
    print(f"Moral compass score: {local_score:.4f}")
    print(f"Formula: 0.94 × ((3+8)/(5+10)) = 0.94 × {11/15:.4f} = {0.94 * (11/15):.4f}")


def demo_progressive_improvement():
    """Demonstrate progressive score improvement"""
    print("DEMO 3: Progressive Challenge Completion")
    print("-" * 70)
    
    from aimodelshare.moral_compass.challenge import ChallengeManager
    
    manager = ChallengeManager(
        table_id="ethics-challenge",
        username="carol",
        api_client=MockApiClient()
    )
    
    stages = [
        ("Stage 1: Initial Model", {"accuracy": 0.80, "fairness": 0.70}, 1, 5),
        ("Stage 2: Improved Fairness", {"accuracy": 0.78, "fairness": 0.88}, 3, 5),
        ("Stage 3: Final Model", {"accuracy": 0.82, "fairness": 0.92}, 5, 5),
    ]
    
    for stage_name, metrics, tasks_done, tasks_total in stages:
        manager.metrics = {}
        manager.primary_metric = None
        
        for name, value in metrics.items():
            primary = (name == "accuracy")
            manager.set_metric(name, value, primary=primary)
        
        manager.set_progress(tasks_completed=tasks_done, total_tasks=tasks_total)
        
        score = manager.get_local_score()
        print(f"\n{stage_name}")
        print(f"  Accuracy: {metrics['accuracy']:.2f}, Fairness: {metrics['fairness']:.2f}")
        print(f"  Progress: {tasks_done}/{tasks_total}")
        print(f"  Score: {score:.4f}")


def demo_leaderboard_sorting():
    """Demonstrate leaderboard sorting"""
    print("DEMO 4: Leaderboard Sorting by Moral Compass Score")
    print("-" * 70)
    
    participants = [
        ("alice_low", 0.70, 2, 10, 0.14),
        ("bob_high", 0.95, 9, 10, 0.855),
        ("carol_mid", 0.80, 5, 10, 0.40),
        ("david_highest", 0.98, 10, 10, 0.98),
    ]
    
    # Sort by score (descending)
    sorted_participants = sorted(participants, key=lambda x: x[4], reverse=True)
    
    print("Leaderboard (sorted by moralCompassScore):\n")
    print(f"{'Rank':<6} {'Username':<15} {'Accuracy':<10} {'Progress':<12} {'Score':<10}")
    print("-" * 70)
    
    for rank, (username, accuracy, tasks_done, tasks_total, score) in enumerate(sorted_participants, 1):
        progress = f"{tasks_done}/{tasks_total}"
        print(f"{rank:<6} {username:<15} {accuracy:<10.2f} {progress:<12} {score:<10.4f}")


def demo_default_primary_metric():
    """Demonstrate default primary metric selection"""
    print("DEMO 5: Default Primary Metric Selection")
    print("-" * 70)
    
    from aimodelshare.moral_compass.challenge import ChallengeManager
    
    # Test 1: With accuracy
    manager1 = ChallengeManager("test", "user1", api_client=MockApiClient())
    manager1.set_metric("robustness", 0.80)
    manager1.set_metric("accuracy", 0.88)
    manager1.set_metric("fairness", 0.90)
    manager1.set_progress(tasks_completed=1, total_tasks=2)
    
    score1 = manager1.get_local_score()
    print("Metrics with 'accuracy' present:")
    print(f"  Available: {list(manager1.metrics.keys())}")
    print(f"  Default primary: accuracy (by convention)")
    print(f"  Score uses: {manager1.metrics['accuracy']:.2f} × (1/2) = {score1:.4f}")
    
    # Test 2: Without accuracy
    manager2 = ChallengeManager("test", "user2", api_client=MockApiClient())
    manager2.set_metric("robustness", 0.80)
    manager2.set_metric("fairness", 0.90)
    manager2.set_progress(tasks_completed=1, total_tasks=2)
    
    score2 = manager2.get_local_score()
    print("\nMetrics without 'accuracy':")
    print(f"  Available: {sorted(manager2.metrics.keys())}")
    print(f"  Default primary: fairness (first alphabetically)")
    print(f"  Score uses: {manager2.metrics['fairness']:.2f} × (1/2) = {score2:.4f}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 70)
    print(" MORAL COMPASS DYNAMIC METRIC SUPPORT - DEMONSTRATION")
    print("=" * 70)
    
    print("\nThis demo shows the new multi-metric tracking capability for")
    print("AI ethics and fairness challenges using the Moral Compass system.")
    
    print_separator()
    demo_basic_usage()
    
    print_separator()
    demo_multi_metric()
    
    print_separator()
    demo_progressive_improvement()
    
    print_separator()
    demo_leaderboard_sorting()
    
    print_separator()
    demo_default_primary_metric()
    
    print("\n" + "=" * 70)
    print(" DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nFor more examples, see:")
    print("  - docs/justice_equity_challenge_example.md")
    print("  - README.md (Moral Compass section)")
    print("  - tests/test_moral_compass_unit.py")
    print()


if __name__ == "__main__":
    main()
