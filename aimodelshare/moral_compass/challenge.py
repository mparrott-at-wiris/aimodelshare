"""
Challenge Manager for Moral Compass system.

Provides a local state manager for tracking multi-metric progress
and syncing with the Moral Compass API.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from .api_client import MoralcompassApiClient


@dataclass
class Question:
    """Represents a challenge question"""
    id: str
    text: str
    options: List[str]
    correct_index: int


@dataclass
class Task:
    """Represents a challenge task"""
    id: str
    title: str
    description: str
    questions: List[Question]


class JusticeAndEquityChallenge:
    """
    Justice & Equity Challenge with predefined tasks and questions.
    
    Contains 6 tasks (A-F) with associated questions for teaching
    ethical AI principles related to fairness and bias.
    """
    
    def __init__(self):
        """Initialize the Justice & Equity Challenge with tasks A-F"""
        self.tasks = [
            Task(
                id="A",
                title="Understanding Algorithmic Bias",
                description="Learn about different types of bias in AI systems",
                questions=[
                    Question(
                        id="A1",
                        text="What is algorithmic bias?",
                        options=[
                            "Bias in the training data",
                            "Systematic and repeatable errors in computer systems",
                            "User preference bias",
                            "Network latency bias"
                        ],
                        correct_index=1
                    )
                ]
            ),
            Task(
                id="B",
                title="Identifying Protected Attributes",
                description="Understanding which attributes require fairness considerations",
                questions=[
                    Question(
                        id="B1",
                        text="Which is a protected attribute in fairness?",
                        options=[
                            "Email address",
                            "Race or ethnicity",
                            "Browser type",
                            "Screen resolution"
                        ],
                        correct_index=1
                    )
                ]
            ),
            Task(
                id="C",
                title="Measuring Disparate Impact",
                description="Learn to measure fairness using statistical metrics",
                questions=[
                    Question(
                        id="C1",
                        text="What is disparate impact?",
                        options=[
                            "Equal outcome rates across groups",
                            "Different outcome rates for different groups",
                            "Same prediction accuracy",
                            "Uniform data distribution"
                        ],
                        correct_index=1
                    )
                ]
            ),
            Task(
                id="D",
                title="Evaluating Model Fairness",
                description="Apply fairness metrics to assess model performance",
                questions=[
                    Question(
                        id="D1",
                        text="What does equal opportunity mean?",
                        options=[
                            "Same accuracy for all groups",
                            "Equal true positive rates across groups",
                            "Equal false positive rates",
                            "Same number of predictions"
                        ],
                        correct_index=1
                    )
                ]
            ),
            Task(
                id="E",
                title="Mitigation Strategies",
                description="Explore techniques to reduce algorithmic bias",
                questions=[
                    Question(
                        id="E1",
                        text="Which is a bias mitigation technique?",
                        options=[
                            "Ignore protected attributes",
                            "Reweighting training samples",
                            "Use more servers",
                            "Faster algorithms"
                        ],
                        correct_index=1
                    )
                ]
            ),
            Task(
                id="F",
                title="Ethical Deployment",
                description="Best practices for deploying fair AI systems",
                questions=[
                    Question(
                        id="F1",
                        text="What is essential for ethical AI deployment?",
                        options=[
                            "Fastest inference time",
                            "Continuous monitoring and auditing",
                            "Most complex model",
                            "Largest dataset"
                        ],
                        correct_index=1
                    )
                ]
            )
        ]
    
    @property
    def total_tasks(self) -> int:
        """Total number of tasks in the challenge"""
        return len(self.tasks)
    
    @property
    def total_questions(self) -> int:
        """Total number of questions across all tasks"""
        return sum(len(task.questions) for task in self.tasks)


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
    
    def __init__(self, table_id: str, username: str, api_client: Optional[MoralcompassApiClient] = None, 
                 challenge: Optional[JusticeAndEquityChallenge] = None):
        """
        Initialize a challenge manager.
        
        Args:
            table_id: The table identifier
            username: The username
            api_client: Optional API client instance (creates new one if None)
            challenge: Optional challenge instance (creates JusticeAndEquityChallenge if None)
        """
        self.table_id = table_id
        self.username = username
        self.api_client = api_client or MoralcompassApiClient()
        self.challenge = challenge or JusticeAndEquityChallenge()
        
        # Metrics state
        self.metrics: Dict[str, float] = {}
        self.primary_metric: Optional[str] = None
        
        # Progress state - initialize with challenge totals
        self.tasks_completed: int = 0
        self.total_tasks: int = self.challenge.total_tasks
        self.questions_correct: int = 0
        self.total_questions: int = self.challenge.total_questions
        
        # Track completed tasks and answers
        self._completed_task_ids: set = set()
        self._answered_questions: Dict[str, int] = {}  # question_id -> selected_index
    
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
    
    def complete_task(self, task_id: str) -> None:
        """
        Mark a task as completed.
        
        Args:
            task_id: The task identifier (e.g., 'A', 'B', 'C')
        """
        if task_id not in self._completed_task_ids:
            self._completed_task_ids.add(task_id)
            self.tasks_completed = len(self._completed_task_ids)
    
    def answer_question(self, task_id: str, question_id: str, selected_index: int) -> bool:
        """
        Record an answer to a question.
        
        Args:
            task_id: The task identifier
            question_id: The question identifier
            selected_index: The index of the selected answer
            
        Returns:
            True if the answer is correct, False otherwise
        """
        # Find the question
        question = None
        for task in self.challenge.tasks:
            if task.id == task_id:
                for q in task.questions:
                    if q.id == question_id:
                        question = q
                        break
                break
        
        if question is None:
            raise ValueError(f"Question {question_id} not found in task {task_id}")
        
        # Record the answer
        self._answered_questions[question_id] = selected_index
        
        # Check if correct and update counter
        is_correct = (selected_index == question.correct_index)
        
        # Recalculate questions_correct
        self.questions_correct = sum(
            1 for qid, idx in self._answered_questions.items()
            if self._is_answer_correct(qid, idx)
        )
        
        return is_correct
    
    def _is_answer_correct(self, question_id: str, selected_index: int) -> bool:
        """Check if an answer is correct"""
        for task in self.challenge.tasks:
            for q in task.questions:
                if q.id == question_id:
                    return selected_index == q.correct_index
        return False
    
    def get_progress_summary(self) -> Dict:
        """
        Get a summary of current progress.
        
        Returns:
            Dictionary with progress information including local score preview
        """
        return {
            'tasksCompleted': self.tasks_completed,
            'totalTasks': self.total_tasks,
            'questionsCorrect': self.questions_correct,
            'totalQuestions': self.total_questions,
            'metrics': self.metrics.copy(),
            'primaryMetric': self.primary_metric,
            'localScorePreview': self.get_local_score()
        }
    
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
