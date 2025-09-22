import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class PromptConfig(BaseModel):
    """Pydantic model for prompt configuration."""

    bare_prompt: str
    output_schema: str
    examples: list[str]


def load_prompt_config(filename: str) -> PromptConfig:
    """Load a prompt configuration from a TOML file."""
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    filepath = prompts_dir / filename

    with open(filepath, "rb") as f:
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


class Config(BaseSettings):
    """Application configuration with automatic environment variable loading."""

    # Environment variables (automatically loaded by Pydantic)
    database_url: str
    openrouter_api_key: str
    swarm_evaluator_mnemonic: str
    use_testnet: bool
    
    # Dynamic fields (set in model_post_init)
    VALIDATION_ONLY_PROMPT: str | None = None
    AI_EVALUATION_SYSTEM_PROMPT: str | None = None

    # Static configuration settings
    PAGINATION_LIMIT: Final[int] = 1000
    INITIAL_LOOKBACK_DAYS: Final[int] = 7
    EVALUATION_SAMPLE_SIZE: Final[int] = 10
    EVALUATION_MIN_SCORE: Final[int] = 0
    EVALUATION_MAX_SCORE: Final[int] = 100
    EVALUATION_INVALID_SCORE: Final[int] = -999
    PENALTY_BASE: Final[float] = 0.1
    PENALTY_ESCALATION: Final[float] = 1.5
    EXTRACTION_ITERATION_SLEEP: Final[int] = 1 * 60 * 60
    LLM_EVALUATION_INTERVAL: Final[int] = 5 * 60
    CURATED_PERMISSION: Final[str] = (
        "0x1f1eea5d5c8d1dc5648bba790eedcc04ab3510dfd6cd035b99e9b1651aa02099"
    )
    # CURATED_PERMISSION: Final[str] = (
    #     "0xb6bb43bf6ad406b43e3e6d317e96188612c037dc70ae758dabc08472e2d5f960"
    # ) # testnet 
    OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: Final[str] = "google/gemini-2.5-flash"

    class Config:
        env_file = "env/.env"

    @property
    def OPENROUTER_API_KEY(self) -> str:
        return self.openrouter_api_key

    @property
    def SWARM_EVALUATOR_MNEMONIC(self) -> str:
        return self.swarm_evaluator_mnemonic

    # Score dimension weights for weighted average calculation
    SCORE_WEIGHTS: Final[dict[str, float]] = {
        "consequentiality": 0.25,
        "actionability": 0.15,
        "foresightedness": 0.2,
        "resolution_clarity": 0.2,
        "verifiability": 0.1,
        "conviction": 0.06,
        "temporal_horizon": 0.04,
    }

    # Quality/Quantity weighting for final score calculation
    QUALITY_WEIGHT: Final[float] = 0.6
    QUANTITY_WEIGHT: Final[float] = 0.4

    def model_post_init(self, _context: Any) -> None:
        """Initialize prompts after Pydantic model creation."""
        # Load prompt configurations from TOML files
        self._validation_config = load_prompt_config("validity_gate.toml")
        self._scoring_config = load_prompt_config("scoring.toml")

        # Validation-only prompt (validity gate only)
        example_outputs = "\n        ".join(self._validation_config.examples)
        self.VALIDATION_ONLY_PROMPT = f"""
        {self._validation_config.bare_prompt}

        {self._validation_config.output_schema}

        Example outputs:
        {example_outputs}
        """

        scoring_example_outputs = "\n        ".join(
            self._scoring_config.examples
        )
        # Full AI Evaluation prompt (validity + quality scoring)
        self.AI_EVALUATION_SYSTEM_PROMPT = f"""
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
CONFIG = Config()  # type: ignore[call-arg]  # Pydantic BaseSettings loads from environment automatically
