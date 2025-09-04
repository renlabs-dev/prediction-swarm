from datetime import datetime, timezone
from time import sleep
from typing import Dict, List

from torusdk._common import get_node_url
from torusdk.client import TorusClient
from torusdk.key import check_ss58_address
from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)

from .api_client import api_client
from .config import CONFIG
from .db.db_service import db_service
from .schemas import Prediction

client = TorusClient(get_node_url(use_testnet=False))


def get_curated_permission_recipients() -> list[Ss58Address]:
    """Get recipients that have the specific curated permission from config."""
    all_permissions = client.query_map(
        "PermissionsByRecipient", module="Permission0", extract_value=False
    )["PermissionsByRecipient"]

    target_permission = CONFIG.CURATED_PERMISSION
    recipients_with_permission: list[Ss58Address] = []

    for recipient, permission_ids in all_permissions.items():
        if target_permission in permission_ids:
            recipients_with_permission.append(check_ss58_address(recipient))

    return recipients_with_permission


def get_predictions(from_date: datetime) -> List[Prediction]:
    """Get all predictions since the given date using pagination."""
    return api_client.fetch_all_predictions(from_date)


def scale_scores_by_quantity(
    quality_scores: Dict[Ss58Address, Dict[str, float]],
    quantity_counts: Dict[str, int],
) -> Dict[Ss58Address, Dict[str, float]]:
    """Scale quality scores by prediction quantity and normalize across all finders.

    Args:
        quality_scores: Quality scores from calculate_normalized_scores_with_penalties()
        quantity_counts: Prediction counts by address from current iteration

    Returns:
        Scaled scores with total contributions normalized to sum to 1.0
    """
    # Calculate total contributions for each finder
    total_contributions: Dict[Ss58Address, float] = {}

    for address, quality_data in quality_scores.items():
        quality_score = quality_data["final_score"]
        prediction_count = quantity_counts.get(address, 0)
        total_contributions[address] = quality_score * prediction_count

    # Normalize so all contributions sum to 1.0
    total_sum = sum(total_contributions.values())

    # Create result with scaled final scores
    result: Dict[Ss58Address, Dict[str, float]] = {}

    for address, quality_data in quality_scores.items():
        result[address] = quality_data.copy()  # Keep original quality data
        result[address]["prediction_count"] = quantity_counts.get(address, 0)
        result[address]["total_contribution"] = total_contributions[address]

        if total_sum > 0:
            result[address]["final_score"] = (
                total_contributions[address] / total_sum
            )
        else:
            result[address]["final_score"] = 0.0

    return result


def get_final_scores(quantity_counts: Dict[str, int]) -> Dict[Ss58Address, int]:
    """Get final scores (quality × quantity) as integers 0-100.

    Args:
        quantity_counts: Prediction counts by address from current iteration

    Returns:
        Dict mapping addresses to final scores (0-100 range)
    """
    quality_scores = db_service.calculate_normalized_scores_with_penalties()

    if not quality_scores:
        return {}

    # Scale quality scores by quantity
    scaled_scores = scale_scores_by_quantity(quality_scores, quantity_counts)

    # Convert to 0-100 integer scores
    final_scores: Dict[Ss58Address, int] = {}
    for address, score_data in scaled_scores.items():
        final_score_int = int(round(score_data["final_score"] * 100))
        final_scores[address] = final_score_int

    return final_scores


def display_latest_scores(quantity_counts: Dict[str, int]) -> None:
    """Display the latest calculated scores for all finder addresses.

    Args:
        quantity_counts: Prediction counts by address from current iteration
    """
    quality_scores = db_service.calculate_normalized_scores_with_penalties()

    if not quality_scores:
        print(
            "No completed evaluation sessions found - scores not available yet"
        )
        return

    # Scale quality scores by quantity
    scores = scale_scores_by_quantity(quality_scores, quantity_counts)

    print(f"\n{'='*80}")
    print("LATEST FINDER SCORES (Quality × Quantity)")
    print(f"{'='*80}")

    # Sort by final score descending
    sorted_scores = sorted(
        scores.items(), key=lambda x: x[1]["final_score"], reverse=True
    )

    print(
        f"{'Rank':<4} {'Address':<16} {'Quality':<7} {'Count':<5} {'Contrib':<7} {'Final%':<7}"
    )
    print(f"{'-'*4} {'-'*16} {'-'*7} {'-'*5} {'-'*7} {'-'*7}")

    for rank, (address, score_data) in enumerate(sorted_scores, 1):
        address_short = f"{address[:8]}...{address[-6:]}"
        quality_score = quality_scores[address][
            "final_score"
        ]  # Normalized quality score across addresses
        prediction_count = int(score_data["prediction_count"])
        contribution = score_data["total_contribution"]
        final_score_pct = score_data["final_score"] * 100

        print(
            f"{rank:<4} {address_short:<16} {quality_score:<7.3f} {prediction_count:<5} {contribution:<7.3f} {final_score_pct:<7.2f}"
        )

    # Summary statistics
    total_addresses = len(scores)
    total_score_sum = sum(s["final_score"] for s in scores.values())
    total_predictions = sum(s["prediction_count"] for s in scores.values())
    total_contribution = sum(s["total_contribution"] for s in scores.values())

    print("\nSUMMARY:")
    print(f"Total addresses evaluated: {total_addresses}")
    print(f"Total predictions in period: {total_predictions}")
    print(f"Total contribution value: {total_contribution:.3f}")
    print(
        f"Final score distribution: {total_score_sum * 100:.1f}% (should be 100.0%)"
    )
    print(f"{'='*80}")


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

    # Calculate and display latest scores if evaluation sessions exist
    display_latest_scores(address_deltas)


if __name__ == "__main__":
    while True:
        # recipients = get_curated_permission_recipients()
        # print(f"Found {recipients} curated permission recipients")
        run_iteration()
        exit(0)
        sleep(CONFIG.EXTRACTION_ITERATION_SLEEP)
