#!/usr/bin/env python3
"""Interactive CLI for human evaluation of predictions."""

import sys
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Dict, List, Optional, Protocol, Tuple

from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)

from .api_client import api_client
from .config import CONFIG
from .db.db_service import db_service
from .db.models import EvaluationSession
from .openrouter_client import openrouter_client
from .schemas import Prediction


class ScoreProvider(Protocol):
    """Protocol for providing prediction scores."""

    def get_score(
        self, prediction: Prediction, index: int, total: int
    ) -> Optional[int]:
        """Get score for a prediction.

        Args:
            prediction: The prediction to score
            index: Current prediction index (1-based)
            total: Total number of predictions

        Returns:
            Score (0-100), CONFIG.EVALUATION_INVALID_SCORE for invalid, or None to quit
        """
        ...


def setup_evaluation_session(
    evaluator_name: str, from_date: datetime, sample_size_per_address: int
) -> Tuple[EvaluationSession, List[Prediction]]:
    """Set up evaluation session with predictions sampling.

    Args:
        evaluator_name: Name of the evaluator
        from_date: Start date for fetching predictions
        sample_size_per_address: Number of predictions to sample per address

    Returns:
        Tuple of (evaluation_session, predictions_to_evaluate)

    Raises:
        Exception: If no predictions found or other errors occur
    """
    print(f"Fetching predictions since {from_date}...")

    # Fetch predictions
    all_predictions = api_client.fetch_all_predictions(from_date)

    if not all_predictions:
        raise Exception("No predictions found for the specified date range.")

    # Show distribution by address before sampling
    address_counts: Dict[Ss58Address, int] = {}
    for pred in all_predictions:
        addr = pred.inserted_by_address
        address_counts[addr] = address_counts.get(addr, 0) + 1

    print(
        f"Found {len(all_predictions)} total predictions from {len(address_counts)} addresses:"
    )
    for addr, count in sorted(
        address_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"  {addr[:8]}...{addr[-8:]}: {count} predictions")
    if len(address_counts) > 10:
        print(f"  ... and {len(address_counts) - 10} more addresses")

    # Sample predictions for evaluation (fair per address)
    predictions_to_evaluate = db_service.sample_predictions_for_evaluation(
        all_predictions, sample_size_per_address
    )

    if not predictions_to_evaluate:
        raise Exception(
            "No new predictions to evaluate (all have already been evaluated)."
        )

    print(f"Sampling {sample_size_per_address} predictions per address...")
    print(f"Total predictions to evaluate: {len(predictions_to_evaluate)}")

    # Create evaluation session
    session = db_service.create_evaluation_session(evaluator_name)
    print(f"Started evaluation session {session.id}")

    return session, predictions_to_evaluate


def get_evaluator_name() -> str:
    """Get the name of the evaluator."""
    while True:
        name = input("Enter your name: ").strip()
        if name:
            return name
        print("Please enter a valid name.")


def get_from_date() -> Optional[datetime]:
    """Get the 'from' date for fetching predictions."""
    print("\nChoose prediction source:")
    print("1. Since last evaluation (default)")
    print("2. Specify custom date")
    print("3. All available predictions")

    choice = input("Choice (1-3, default: 1): ").strip() or "1"

    if choice == "1":
        last_eval = db_service.get_last_evaluation_timestamp()
        if last_eval:
            print(f"Using last evaluation date: {last_eval}")
            return last_eval
        else:
            print("No previous evaluations found. Using initial start date.")
            return CONFIG.get_initial_start_date()
    elif choice == "2":
        while True:
            date_str = input("Enter date (YYYY-MM-DD): ").strip()
            try:
                return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD")
    elif choice == "3":
        return CONFIG.get_initial_start_date()
    else:
        print("Invalid choice, using default (last evaluation)")
        return (
            db_service.get_last_evaluation_timestamp()
            or CONFIG.get_initial_start_date()
        )


def get_sample_size() -> int:
    """Get the number of predictions to evaluate per address."""
    default = CONFIG.EVALUATION_SAMPLE_SIZE
    size_input = input(
        f"Number of predictions to evaluate PER ADDRESS (default: {default}): "
    ).strip()

    if not size_input:
        return default

    try:
        size = int(size_input)
        if size <= 0:
            print("Sample size must be positive. Using default.")
            return default
        return size
    except ValueError:
        print("Invalid number. Using default.")
        return default


def display_prediction(
    prediction: Prediction, current: int, total: int
) -> None:
    """Display a prediction for evaluation."""
    print(f"\n{'='*80}")
    print(f"[{current}/{total}] Prediction ID: {prediction.id}")
    print(f"{'='*80}")

    # Show full post (primary focus)
    print("FULL POST:")
    print(f"{prediction.full_post}")
    print(f"{'-'*80}")

    # Show context if available
    if prediction.context:
        print("CONTEXT:")
        print(f"{prediction.context}")
        print(f"{'-'*80}")

    # Show metadata
    print("METADATA:")
    print(f"Posted by: {prediction.predictor_twitter_username}")
    print(f"Posted at: {prediction.prediction_timestamp}")
    print(f"Topic: {prediction.topic}")
    print(f"URL: {prediction.url}")
    print(f"Verification claims: {len(prediction.verification_claims)}")
    
    # Show extracted prediction (de-emphasized, for reference only)
    print(f"Extracted prediction (reference): {prediction.prediction[:100]}{'...' if len(prediction.prediction) > 100 else ''}")
    print(f"{'='*80}")


class ManualScoreProvider:
    """Score provider for manual CLI evaluation."""

    def get_score(
        self, prediction: Prediction, index: int, total: int
    ) -> Optional[int]:
        """Get manual score from user input."""
        display_prediction(prediction, index, total)
        return get_manual_score()


class LLMScoreProvider:
    """Score provider for LLM-based evaluation."""

    def __init__(self) -> None:
        self.last_reason: Optional[str] = None

    def get_score(
        self, prediction: Prediction, index: int, total: int
    ) -> Optional[int]:
        """Get score from LLM evaluation."""
        print(
            f"[{index}/{total}] Evaluating prediction {prediction.id} with LLM..."
        )

        # Get full response with score and reason
        response = openrouter_client.evaluate_prediction_full(prediction)
        if response is None:
            print("  LLM evaluation failed - skipping")
            self.last_reason = None
            return -1  # Skip this prediction

        # Store the reason for later use
        self.last_reason = response.brief_rationale

        if not response.valid:
            print("  LLM marked as INVALID")
            if response.brief_rationale:
                print(f"  Reason: {response.brief_rationale}")
            return CONFIG.EVALUATION_INVALID_SCORE
        else:
            # Calculate weighted average of the 7 dimension scores
            if response.scores:
                weighted_score = 0.0
                for dimension, score in response.scores.items():
                    weight = CONFIG.SCORE_WEIGHTS.get(dimension, 0.0)
                    weighted_score += score * weight
                final_score = max(0, min(100, int(round(weighted_score))))
                print(f"  LLM Score: {final_score} (weighted avg of {dict(response.scores)})")
                return final_score
            else:
                print("  No scores provided for valid prediction")
                return -1  # Skip this prediction


def get_manual_score() -> Optional[int]:
    """Get score input from user."""
    while True:
        user_input = (
            input(
                f"Score ({CONFIG.EVALUATION_MIN_SCORE}-{CONFIG.EVALUATION_MAX_SCORE}, "
                "'i' for invalid, 's' to skip, 'q' to quit): "
            )
            .strip()
            .lower()
        )

        if user_input == "q":
            return None  # Signal to quit
        elif user_input == "s":
            return -1  # Signal to skip
        elif user_input == "i":
            return CONFIG.EVALUATION_INVALID_SCORE  # Signal invalid prediction

        try:
            score = int(user_input)
            if (
                CONFIG.EVALUATION_MIN_SCORE
                <= score
                <= CONFIG.EVALUATION_MAX_SCORE
            ):
                return score
            else:
                print(
                    f"Score must be between {CONFIG.EVALUATION_MIN_SCORE} and {CONFIG.EVALUATION_MAX_SCORE}"
                )
        except ValueError:
            print(
                "Please enter a valid number, 'i' for invalid, 's' to skip, or 'q' to quit"
            )


def run_evaluation_with_provider(
    score_provider: ScoreProvider,
    evaluator_name: str,
    from_date: Optional[datetime] = None,
    sample_size_per_address: Optional[int] = None,
) -> None:
    """Run evaluation using the provided score provider.

    Args:
        score_provider: Provider for getting prediction scores
        evaluator_name: Name of the evaluator
        from_date: Start date for predictions (if None, will be determined)
        sample_size_per_address: Sample size per address (if None, will be determined)
    """
    try:
        # Setup evaluation session
        session, predictions_to_evaluate = setup_evaluation_session(
            evaluator_name,
            from_date or datetime.now(timezone.utc),
            sample_size_per_address or CONFIG.EVALUATION_SAMPLE_SIZE,
        )

        # Evaluate predictions
        evaluated_count = 0
        skipped_count = 0
        invalid_count = 0

        try:
            for i, prediction in enumerate(predictions_to_evaluate, 1):
                score = score_provider.get_score(
                    prediction, i, len(predictions_to_evaluate)
                )

                if score is None:  # Quit requested
                    print("\nEvaluation interrupted.")
                    break
                elif score == -1:  # Skip requested (manual only)
                    print("Skipped.")
                    skipped_count += 1
                    continue
                elif (
                    score == CONFIG.EVALUATION_INVALID_SCORE
                ):  # Invalid prediction
                    invalid_count += 1
                else:
                    evaluated_count += 1

                # Store evaluation with additional fields
                full_text = getattr(prediction, "full_post", None)
                score_reason = (
                    getattr(score_provider, "last_reason", None)
                    if hasattr(score_provider, "last_reason")
                    else None
                )

                db_service.store_evaluation(
                    session_id=session.id,
                    prediction_id=prediction.id,
                    prediction_text=prediction.prediction,
                    finder_key=prediction.inserted_by_address,
                    score=score,
                    full_text=full_text,
                    score_reason=score_reason,
                )

            # Complete session
            db_service.complete_evaluation_session(session.id)

            # Show summary
            print(f"\n{'='*50}")
            print("Evaluation Summary:")
            print(f"Evaluated: {evaluated_count} predictions")
            print(f"Invalid: {invalid_count} predictions")
            if skipped_count > 0:
                print(f"Skipped: {skipped_count} predictions")
            print(f"Session ID: {session.id}")
            print("Evaluation completed!")

        except KeyboardInterrupt:
            print("\n\nEvaluation interrupted. Session saved.")
            db_service.complete_evaluation_session(session.id)

    except Exception as e:
        print(f"Error during evaluation: {e}")
        return


def run_evaluation(from_date: Optional[datetime] = None) -> None:
    """Run manual evaluation process."""
    print("Welcome to the Prediction Evaluator!")
    print("=" * 50)

    # Get evaluator information
    evaluator_name = get_evaluator_name()

    # Determine from_date if not provided
    if from_date is None:
        from_date = get_from_date()

    # Get sample size per address
    sample_size_per_address = get_sample_size()

    # Use unified evaluation engine with manual score provider
    run_evaluation_with_provider(
        ManualScoreProvider(),
        evaluator_name,
        from_date,
        sample_size_per_address,
    )


def run_llm_evaluation() -> None:
    """Run LLM-based evaluation in a loop every 30 minutes."""
    print("Welcome to the LLM Prediction Evaluator!")
    print("=" * 50)
    print(f"Running every {CONFIG.LLM_EVALUATION_INTERVAL // 60} minutes...")

    while True:
        print(f"\n{'='*60}")
        print(f"Starting LLM evaluation cycle at {datetime.now(timezone.utc)}")
        print(f"{'='*60}")

        # Test OpenRouter connection first
        if not openrouter_client.test_connection():
            print(
                "Cannot proceed with LLM evaluation - OpenRouter connection failed."
            )
            print(f"Retrying in {CONFIG.LLM_EVALUATION_INTERVAL // 60} minutes...")
        else:
            # Set evaluator name for LLM
            evaluator_name = f"LLM-{CONFIG.OPENROUTER_MODEL}"

            # Use last 24 hours
            yesterday = datetime.now(timezone.utc) - timedelta(days=2)

            print(f"Evaluating predictions from the last 24 hours (since {yesterday})")

            try:
                # Use unified evaluation engine with LLM score provider
                run_evaluation_with_provider(
                    LLMScoreProvider(),
                    evaluator_name,
                    yesterday,
                    CONFIG.EVALUATION_SAMPLE_SIZE,
                )
                print("LLM evaluation cycle completed successfully!")
            except Exception as e:
                print(f"Error during LLM evaluation: {e}")
                print(f"Will retry in {CONFIG.LLM_EVALUATION_INTERVAL // 60} minutes...")

        # Sleep for 30 minutes before next cycle
        print(f"Sleeping for {CONFIG.LLM_EVALUATION_INTERVAL // 60} minutes...")
        sleep(CONFIG.LLM_EVALUATION_INTERVAL)


def show_stats() -> None:
    """Show evaluation statistics."""
    stats = db_service.get_evaluation_stats()
    print("Evaluation Statistics:")
    print(f"Total evaluations: {stats['total_evaluations']}")
    print(f"Completed sessions: {stats['completed_sessions']}")
    print(f"Average score: {stats['average_score']}")


def main() -> None:
    """Main entry point for the evaluator CLI."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            show_stats()
            return
        elif sys.argv[1] == "llm":
            run_llm_evaluation()
            return
        elif sys.argv[1] == "from" and len(sys.argv) > 2:
            try:
                from_date = datetime.fromisoformat(
                    f"{sys.argv[2]}T00:00:00+00:00"
                )
                run_evaluation(from_date)
                return
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD")
                return
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python evaluator.py           - Manual evaluation")
            print("  python evaluator.py llm       - LLM evaluation (last 24h)")
            print(
                "  python evaluator.py stats     - Show evaluation statistics"
            )
            print(
                "  python evaluator.py from DATE - Manual evaluation from specific date (YYYY-MM-DD)"
            )
            return

    run_evaluation()


if __name__ == "__main__":
    main()
