from datetime import datetime, timezone
from typing import List

from db.db_service import db_service

from .api_client import api_client
from .config import CONFIG
from .schemas import Prediction


def get_predictions(from_date: datetime) -> List[Prediction]:
    """Get all predictions since the given date using pagination."""
    return api_client.fetch_all_predictions(from_date)


def run_iteration() -> None:
    """Run a complete iteration: fetch predictions and store results in database."""
    run_timestamp = datetime.now(timezone.utc)
    print(f"Starting iteration at {run_timestamp}")

    # Determine the 'from' date for fetching predictions
    last_run = db_service.get_last_run_timestamp()
    if last_run:
        from_date = last_run
        print(f"Last run was at {last_run} - fetching predictions since then")
    else:
        from_date = CONFIG.get_initial_start_date()
        print(f"This is the first run - fetching predictions since {from_date}")

    # Fetch predictions
    predictions = get_predictions(from_date)

    # Count predictions by address (total counts)
    current_totals = db_service.count_predictions_by_address(predictions)
    print(f"Found predictions from {len(current_totals)} unique addresses")

    # Get previous totals and calculate deltas
    previous_totals = db_service.get_previous_address_totals()
    address_deltas = db_service.calculate_address_deltas(
        current_totals, previous_totals
    )

    # Show results
    print(
        f"Addresses with new predictions since last run: {len(address_deltas)}"
    )
    for address, delta in sorted(
        address_deltas.items(), key=lambda x: x[1], reverse=True
    ):
        total = current_totals[address]
        print(f"  {address[:8]}...{address[-8:]}: +{delta} (total: {total})")

    # Store iteration in database
    iteration = db_service.store_iteration(
        run_timestamp=run_timestamp,
        predictions=predictions,
        address_deltas=address_deltas,
        address_totals=current_totals,
    )

    print(f"Stored iteration {iteration.id} in database")


if __name__ == "__main__":
    run_iteration()
