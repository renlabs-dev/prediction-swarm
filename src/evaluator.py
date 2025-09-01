#!/usr/bin/env python3
"""Interactive CLI for human evaluation of predictions."""

import sys
from datetime import datetime
from typing import Dict, Optional

from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)

from .api_client import api_client
from .config import CONFIG
from .db.db_service import db_service
from .schemas import Prediction


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
    
    # Show full post
    print("FULL POST:")
    print(f"{prediction.full_post}")
    print(f"{'-'*80}")
    
    # Show extracted prediction
    print("EXTRACTED PREDICTION:")
    print(f"{prediction.prediction}")
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
    print(f"{'='*80}")


def get_score() -> Optional[int]:
    """Get score input from user."""
    while True:
        user_input = (
            input(
                f"Score ({CONFIG.EVALUATION_MIN_SCORE}-{CONFIG.EVALUATION_MAX_SCORE}, "
                "'s' to skip, 'q' to quit): "
            )
            .strip()
            .lower()
        )

        if user_input == "q":
            return None  # Signal to quit
        elif user_input == "s":
            return -1  # Signal to skip

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
            print("Please enter a valid number, 's' to skip, or 'q' to quit")


def run_evaluation(from_date: Optional[datetime] = None) -> None:
    """Run the evaluation process."""
    print("Welcome to the Prediction Evaluator!")
    print("=" * 50)

    # Get evaluator information
    evaluator_name = get_evaluator_name()

    # Determine from_date if not provided
    if from_date is None:
        from_date = get_from_date()

    # Get sample size per address
    sample_size_per_address = get_sample_size()

    print(f"\nFetching predictions since {from_date}...")

    # Fetch predictions
    try:
        # from_date should not be None at this point, but let's be safe
        if from_date is None:
            print("Error: No valid from_date provided")
            return
        all_predictions = api_client.fetch_all_predictions(from_date)
    except Exception as e:
        print(f"Error fetching predictions: {e}")
        return

    if not all_predictions:
        print("No predictions found for the specified date range.")
        return

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
        print(
            "No new predictions to evaluate (all have already been evaluated)."
        )
        return

    print(f"Sampling {sample_size_per_address} predictions per address...")
    print(f"Total predictions to evaluate: {len(predictions_to_evaluate)}")

    # Create evaluation session
    session = db_service.create_evaluation_session(evaluator_name)
    print(f"Started evaluation session {session.id}")

    # Evaluate predictions
    evaluated_count = 0
    skipped_count = 0

    try:
        for i, prediction in enumerate(predictions_to_evaluate, 1):
            display_prediction(prediction, i, len(predictions_to_evaluate))

            score = get_score()

            if score is None:  # Quit requested
                print("\nEvaluation interrupted by user.")
                break
            elif score == -1:  # Skip requested
                print("Skipped.")
                skipped_count += 1
                continue

            # Store evaluation
            db_service.store_evaluation(
                session_id=session.id,
                prediction_id=prediction.id,
                prediction_text=prediction.prediction,
                score=score,
            )
            evaluated_count += 1
            print(f"Scored: {score}")

        # Complete session
        db_service.complete_evaluation_session(session.id)

        # Show summary
        print(f"\n{'='*50}")
        print("Evaluation Summary:")
        print(f"Evaluated: {evaluated_count} predictions")
        print(f"Skipped: {skipped_count} predictions")
        print(f"Session ID: {session.id}")
        print("Thank you for your evaluations!")

    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted. Session saved.")
        db_service.complete_evaluation_session(session.id)
    except Exception as e:
        print(f"\nError during evaluation: {e}")
        print("Session will be marked as incomplete.")


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

    run_evaluation()


if __name__ == "__main__":
    main()
