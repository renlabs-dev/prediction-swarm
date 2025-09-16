import os
from datetime import datetime
from typing import Final

from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/.env", override=False)


class MemoryUrl:
    """Singleton configuration class for API endpoints."""

    _instance: "MemoryUrl | None" = None

    def __new__(cls) -> "MemoryUrl":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # API Base URL
        self.BASE: Final[str] = "https://memory.sension.torus.directory/api/"

        # Authentication endpoints
        self.CHALLENGE: Final[str] = f"{self.BASE}auth/challenge"
        self.VERIFY: Final[str] = f"{self.BASE}auth/verify"

        # Predictions endpoints
        self.LIST_PREDICTIONS: Final[str] = f"{self.BASE}predictions/list"


class Config:
    """Application configuration."""

    _instance: "Config | None" = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Pagination settings
        self.PAGINATION_LIMIT: Final[int] = 1000  # API max limit

        # Time settings
        self.INITIAL_LOOKBACK_DAYS: Final[int] = (
            7  # Look back 7 days for first run
        )

        # Evaluation settings
        self.EVALUATION_SAMPLE_SIZE: Final[int] = (
            10  # Default number of predictions to evaluate
        )
        self.EVALUATION_MIN_SCORE: Final[int] = 0  # Minimum score
        self.EVALUATION_MAX_SCORE: Final[int] = 100  # Maximum score
        self.EVALUATION_INVALID_SCORE: Final[
            int
        ] = -999  # Invalid prediction marker

        # Penalty system for invalid predictions
        self.PENALTY_BASE: Final[float] = 0.1  # Base penalty magnitude (P)
        self.PENALTY_ESCALATION: Final[float] = 1.5  # Escalation factor (r)

        self.EXTRACTION_ITERATION_SLEEP: Final[int] = 1 * 60 * 60

        self.CURATED_PERMISSION: Final[str] = (
            "0x1f1eea5d5c8d1dc5648bba790eedcc04ab3510dfd6cd035b99e9b1651aa02099"
        )

        # OpenRouter AI Evaluation settings
        # Note: Pull from the correct env var name: OPENROUTER_API_KEY
        self.OPENROUTER_API_KEY: Final[str] = os.getenv("OPENROUTER_API_KEY", "")
        self.OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"
        self.OPENROUTER_MODEL: Final[str] = "deepseek/deepseek-chat-v3.1"

        # AI Evaluation prompt
        self.AI_EVALUATION_SYSTEM_PROMPT: Final[
            str
        ] = r"""You are an expert evaluator of predictions and forecasts. Your task is to score predictions on their accuracy, specificity, and overall quality.

            - Valid Prediction Checklist
            A submitted item is valid if it passes all checks:

            Consequential: Non-trivial, domain-relevant, and not purely local/personal.
            Attributable & timestamped: Clear author and verifiable publication time.
            Well-defined: Outcome is measurable with explicit resolution source, units, and tie-breaks.
            Evaluable: Structured so it can be scored (format + proper scoring rule).
            Resolvable: Clear path to adjudication, including conditions or revisions.

            - Scoring
            Total score ranges from 0 to 100, the influencing factors sorted by relevance are:

            Consequentiality — Should make up most of the prediction quality.
            If a prediction is not consequential, quality goes instantly to 0.

            Verifiability — Prediction should ideally be easily verifiable.
            If it is consequential but hard to evaluate, quality goes down.

            Clarity & Specificity — Predictions should use precise metrics, explicit timelines, and clear conditions.
            Ambiguous or vague claims lower quality.

            Return a json with the fields: 
                {score: only an integer score between 0-100. or INVALID if the prediction is considered invalid}.
                {reason: a string explaining why the prediction is invalid} // for when the score is INVALID
            answer with nothing but the json response.
            Dont forget: answer with just {score: int | INVALID, reason: str | None}.
            Nothing else. Make no mistakes or ill go to hell.
            Answer with nothing but the json response startin with '{' and ending with '}'.
            """

    def get_initial_start_date(self) -> datetime:
        """Get the hardcoded initial start date for predictions."""
        # Hardcoded start date: August 25, 2025 (7 days before Sep 1, 2025)
        return datetime.fromisoformat("2025-08-25T00:00:00+00:00")


# Global instances
MEMORY_URL = MemoryUrl()
CONFIG = Config()
