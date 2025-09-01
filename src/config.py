from datetime import datetime
from typing import Final


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

    def get_initial_start_date(self) -> datetime:
        """Get the hardcoded initial start date for predictions."""
        # Hardcoded start date: August 25, 2025 (7 days before Sep 1, 2025)
        return datetime.fromisoformat("2025-08-25T00:00:00+00:00")


# Global instances
MEMORY_URL = MemoryUrl()
CONFIG = Config()
