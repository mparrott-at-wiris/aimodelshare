"""
Challenge Manager for Moral Compass system.

Provides a local state manager for tracking multi-metric progress
and syncing with the Moral Compass API.
"""

from typing import Dict, Optional
from .api_client import MoralcompassApiClient


class ChallengeManager:
    """
    Manages local state for a user's challenge progress with multiple metrics.
    
    Features:
    - Track arbitrary metrics (accuracy, fairness, robustness, etc.)
    - Specify primary metric for scoring
    - Track task and question progress
    - Local preview of moral compass score
    - Sync to server via API
    """
    
    def __init__(self, table_id: str, username: str, api_client: Optional[MoralcompassApiClient] = None):
        """
        Initialize a challenge manager.
        
        Args:
            table_id: The table identifier
            username: The username
            api_client: Optional API client instance (creates new one if None)
        """
        self.table_id = table_id
        self.username = username
        self.api_client = api_client or MoralcompassApiClient()
        
        # Metrics state
        self.metrics: Dict[str, float] = {}
        self.primary_metric: Optional[str] = None
        
        # Progress state
        self.tasks_completed: int = 0
        self.total_tasks: int = 0
        self.questions_correct: int = 0
        self.total_questions: int = 0
    
    def set_metric(self, name: str, value: float, primary: bool = False) -> None:
        """
        Set a metric value.
        
        Args:
            name: Metric name (e.g., 'accuracy', 'fairness', 'robustness')
            value: Metric value (should be between 0 and 1 typically)
            primary: If True, sets this as the primary metric for scoring
        """
        self.metrics[name] = value
        
        if primary:
            self.primary_metric = name
        elif self.primary_metric is None and len(self.metrics) == 1:
            # Auto-set first metric as primary if none set
            self.primary_metric = name
    
    def set_progress(self, tasks_completed: int = 0, total_tasks: int = 0,
                    questions_correct: int = 0, total_questions: int = 0) -> None:
        """
        Set progress counters.
        
        Args:
            tasks_completed: Number of tasks completed
            total_tasks: Total number of tasks
            questions_correct: Number of questions answered correctly
            total_questions: Total number of questions
        """
        self.tasks_completed = tasks_completed
        self.total_tasks = total_tasks
        self.questions_correct = questions_correct
        self.total_questions = total_questions
    
    def get_local_score(self) -> float:
        """
        Calculate moral compass score locally without syncing to server.
        
        Returns:
            Moral compass score based on current state
        """
        if not self.metrics:
            return 0.0
        
        # Determine primary metric
        primary_metric = self.primary_metric
        if primary_metric is None:
            if 'accuracy' in self.metrics:
                primary_metric = 'accuracy'
            else:
                primary_metric = sorted(self.metrics.keys())[0]
        
        primary_value = self.metrics.get(primary_metric, 0.0)
        
        # Calculate progress ratio
        progress_denominator = self.total_tasks + self.total_questions
        if progress_denominator == 0:
            return 0.0
        
        progress_ratio = (self.tasks_completed + self.questions_correct) / progress_denominator
        
        return primary_value * progress_ratio
    
    def sync(self) -> Dict:
        """
        Sync current state to the Moral Compass API.
        
        Returns:
            API response dict with moralCompassScore and other fields
        """
        if not self.metrics:
            raise ValueError("No metrics set. Use set_metric() before syncing.")
        
        return self.api_client.update_moral_compass(
            table_id=self.table_id,
            username=self.username,
            metrics=self.metrics,
            tasks_completed=self.tasks_completed,
            total_tasks=self.total_tasks,
            questions_correct=self.questions_correct,
            total_questions=self.total_questions,
            primary_metric=self.primary_metric
        )
    
    def __repr__(self) -> str:
        return (
            f"ChallengeManager(table_id={self.table_id!r}, username={self.username!r}, "
            f"metrics={self.metrics}, primary_metric={self.primary_metric!r}, "
            f"local_score={self.get_local_score():.4f})"
        )
