import os
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv("env/.env")


class PromptConfig(BaseModel):
    """Pydantic model for prompt configuration."""
    bare_prompt: str
    output_schema: str
    examples: list[str]


def load_prompt_config(filename: str) -> PromptConfig:
    """Load a prompt configuration from a TOML file."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    filepath = prompts_dir / filename
    
    with open(filepath, 'rb') as f:
        data = tomllib.load(f)
        return PromptConfig.model_validate(data)


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
        self.LLM_EVALUATION_INTERVAL: Final[int] = 5 * 60  # 5 minutes

        self.CURATED_PERMISSION: Final[str] = (
            "0x1f1eea5d5c8d1dc5648bba790eedcc04ab3510dfd6cd035b99e9b1651aa02099"
        )

        # OpenRouter AI Evaluation settings
        self.OPENROUTER_API_KEY: Final[str] = os.getenv("OPENROUTER_URL", "")
        self.OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"
        self.OPENROUTER_MODEL: Final[str] = "google/gemini-2.5-flash"

        # Score dimension weights for weighted average calculation
        self.SCORE_WEIGHTS: Final[dict[str, float]] = {
            "consequentiality": 0.25,
            "actionability": 0.15,
            "foresightedness": 0.2,
            "resolution_clarity": 0.2,
            "verifiability": 0.1,
            "conviction": 0.06,
            "temporal_horizon": 0.04,
        }

        # Quality/Quantity weighting for final score calculation
        self.QUALITY_WEIGHT: Final[float] = 0.6
        self.QUANTITY_WEIGHT: Final[float] = 0.4

        # Load prompt configurations from TOML files
        self._validation_config = load_prompt_config("validity_gate.toml")
        self._scoring_config = load_prompt_config("scoring.toml")
        
        # Validation-only prompt (validity gate only)
        example_outputs = '\n        '.join(self._validation_config.examples)
        self.VALIDATION_ONLY_PROMPT: Final[str] = f"""
        {self._validation_config.bare_prompt}

        {self._validation_config.output_schema}

        Example outputs:
        {example_outputs}
        """

        scoring_example_outputs = '\n        '.join(self._scoring_config.examples)
        # Full AI Evaluation prompt (validity + quality scoring)
        self.AI_EVALUATION_SYSTEM_PROMPT: Final[str] = f"""
        {self._scoring_config.bare_prompt}

        {self._scoring_config.output_schema}

        Example outputs:
        {scoring_example_outputs}
        """

    def get_initial_start_date(self) -> datetime:
        """Get the hardcoded initial start date for predictions."""
        # Hardcoded start date: August 25, 2025 (7 days before Sep 1, 2025)
        return datetime.fromisoformat("2025-08-25T00:00:00+00:00")


# Global instances
MEMORY_URL = MemoryUrl()
CONFIG = Config()
