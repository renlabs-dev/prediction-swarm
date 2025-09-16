import os
from datetime import datetime
from typing import Final

from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/.env")


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

        # AI Evaluation prompt
        self.AI_EVALUATION_SYSTEM_PROMPT: Final[str] = r"""
You evaluate predictions for validity, and if valid, for quality across a set of dimensions.

VALIDITY GATE
A valid prediction is a verifiable claim about an uncertain future outcome that matters beyond those who control it.

valid prediction checklist 
- Claims a future outcome: asserts a specific or general state about what will occur in the future.
- Outcome is uncertain: The prediction is non-trivial and non-obvious.
- Outcome is verifiable in principle: an observer could examine future evidence and make a reasonable judgement whether the prediction held true, even if not with full precision or confidence.
- Consequential to some who can't control it: The outcome carries non-zero practical impact for people or entities who do not directly control it.

Conditional predictions ("if X then Y") are valid.

QUALITY SCORING (0-100 per dimension)

Consequentiality: how significant are the stakes of the outcome?

Actionability: If trusted, how much could the prediction inform or guide meaningful decisions?

Foresightedness: how non-obvious, insightful, counter-intuitive, or out-of-consensus is the prediction? What level of intellect or discernment is required to make it?

Resolution clarity: how specific is the claimed outcome and timeline?

Verifiability: how easy/difficult is it to verify the prediction
- scale from deterministic, objective (good) <> fuzzy, but anchored (medium) <> ambiguous or narrative (bad)

Conviction level: how confident is the prediction? higher confidence is better. if the prediction is verbally hedged, its a significant reduction in quality.
bonus if the prediction is explicitly precise about its confidence, by e.g. stating "p(0.92)" or "im very confident about this.".

Temporal horizon: What is the expected duration until resolution. Shorter is better.
- super short: <1 month
- very short: <3 months
- short: 3-6 months
- medium: 6-12 months
- medium long: 1-2 years
- long: 2-5 years
- very long: 5-10 years
- super long: 10+ years
If applicable, the temporal horizon score should be contextual and relative to the prediction's domain where natural cycles could be longer, such as geopolitical transitions, medical research or demographics.
If there is no clear temporal horizon, that is bad.

OUTPUT FORMAT
Return ONLY a valid JSON object. Do not include markdown code fences, backticks, or any other formatting.

{
 "valid": boolean,
 "scores": {
   "consequentiality": int,
   "actionability": int,
   "foresightedness": int,
   "resolution_clarity": int,
   "verifiability": int,
   "conviction": int,
   "temporal_horizon": int
 },
 "brief_rationale": string (max 100 words)
}

If invalid, the rationale should explain why and score null. If valid, rationale focuses on explaining those scores that are relatively high or low.
"""

    def get_initial_start_date(self) -> datetime:
        """Get the hardcoded initial start date for predictions."""
        # Hardcoded start date: August 25, 2025 (7 days before Sep 1, 2025)
        return datetime.fromisoformat("2025-08-25T00:00:00+00:00")


# Global instances
MEMORY_URL = MemoryUrl()
CONFIG = Config()
