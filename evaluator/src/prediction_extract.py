import argparse
from datetime import datetime, timezone
from time import sleep
from typing import Dict, List, Optional

from torusdk._common import get_node_url
from torusdk.client import TorusClient
from torusdk.key import check_ss58_address, Keypair
from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)

from .api_client import api_client
from .config import CONFIG
from .db.db_service import db_service
from .schemas import Prediction
from .stream_weights import update_curated_permission_weights

client = TorusClient(get_node_url(use_testnet=CONFIG.use_testnet))


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


def count_predictions_by_address(
    predictions: List[Prediction],
) -> Dict[Ss58Address, int]:
    """Count predictions by wallet address."""
    from collections import defaultdict

    counts: Dict[Ss58Address, int] = defaultdict(int)
    for prediction in predictions:
        counts[prediction.inserted_by_address] += 1
    return dict(counts)


def scale_scores_by_quantity(
    quality_scores: Dict[Ss58Address, Dict[str, float]],
    quantity_counts: Dict[Ss58Address, int],
) -> Dict[Ss58Address, Dict[str, float]]:
    """Combine quality scores with quantity scores using weighted approach (0.6/0.4).
    Final scores are normalized to sum to 1.0.

    Args:
        quality_scores: Quality scores from calculate_normalized_scores_with_penalties()
        quantity_counts: Prediction counts by address from current iteration

    Returns:
        Weighted scores normalized to sum to 1.0
    """
    # Normalize quantity scores to 0-1 range
    max_quantity = max(quantity_counts.values()) if quantity_counts else 0
    normalized_quantity: Dict[Ss58Address, float] = {}
    
    for address in quality_scores.keys():
        quantity = quantity_counts.get(address, 0)
        normalized_quantity[address] = quantity / max_quantity if max_quantity > 0 else 0.0

    # Calculate weighted scores for each finder
    weighted_scores: Dict[Ss58Address, float] = {}

    for address, quality_data in quality_scores.items():
        quality_score = quality_data["final_score"]
        quantity_score = normalized_quantity[address]
        
        weighted_score = (
            quality_score * CONFIG.QUALITY_WEIGHT + 
            quantity_score * CONFIG.QUANTITY_WEIGHT
        )
        weighted_scores[address] = weighted_score

    # Normalize so all weighted scores sum to 1.0
    total_sum = sum(weighted_scores.values())

    # Create result with weighted final scores
    result: Dict[Ss58Address, Dict[str, float]] = {}

    for address, quality_data in quality_scores.items():
        result[address] = quality_data.copy()  # Keep original quality data
        result[address]["prediction_count"] = quantity_counts.get(address, 0)
        result[address]["normalized_quantity"] = normalized_quantity[address]
        result[address]["weighted_score"] = weighted_scores[address]

        if total_sum > 0:
            result[address]["final_score"] = weighted_scores[address] / total_sum
        else:
            result[address]["final_score"] = 0.0

    return result


def get_final_scores(
    quantity_counts: Dict[Ss58Address, int],
) -> Dict[Ss58Address, int]:
    """Get final scores (quality × quantity) as integers 0-100.

    Args:
        quantity_counts: Prediction counts by address from current iteration

    Returns:
        Dict mapping addresses to final scores (0-100 range)
    """
    curated_finders = get_curated_permission_recipients()
    quality_scores = db_service.calculate_normalized_scores_with_penalties(
        curated_finders
    )

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


def display_latest_scores(quantity_counts: Dict[Ss58Address, int]) -> None:
    """Display the latest calculated scores for all finder addresses.

    Args:
        quantity_counts: Prediction counts by address from current iteration
    """
    curated_finders = get_curated_permission_recipients()
    quality_scores = db_service.calculate_normalized_scores_with_penalties(
        curated_finders
    )

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
        f"{'Rank':<4} {'Address':<16} {'Quality':<7} {'Count':<5} {'Penalty':<7} {'Final%':<7}"
    )
    print(f"{'-'*4} {'-'*16} {'-'*7} {'-'*5} {'-'*7} {'-'*7}")

    for rank, (address, score_data) in enumerate(sorted_scores, 1):
        address_short = f"{address[:8]}...{address[-6:]}"
        quality_score = quality_scores[address][
            "final_score"
        ]  # Normalized quality score across addresses
        prediction_count = int(score_data["prediction_count"])
        penalty = score_data.get("penalty", 0.0)
        final_score_pct = score_data["final_score"] * 100

        print(
            f"{rank:<4} {address_short:<16} {quality_score:<7.3f} {prediction_count:<5} {penalty:<7.3f} {final_score_pct:<7.2f}"
        )

    # Summary statistics
    total_addresses = len(scores)
    total_score_sum = sum(s["final_score"] for s in scores.values())
    total_predictions = sum(int(s["prediction_count"]) for s in scores.values())
    avg_penalty = sum(s.get("penalty", 0.0) for s in scores.values()) / len(scores) if scores else 0

    print("\nSUMMARY:")
    print(f"Total addresses evaluated: {total_addresses}")
    print(f"Total predictions in period: {total_predictions}")
    print(f"Average penalty: {avg_penalty:.3f}")
    print(
        f"Final score distribution: {total_score_sum * 100:.1f}% (should be 100.0%)"
    )
    print(f"{'='*80}")


def run_iteration(dry_run: bool = False) -> None:
    """Run a complete iteration: fetch predictions and store results in database.
    
    Args:
        dry_run: If True, read from chain/db but skip all writes
    """
    run_timestamp = datetime.now(timezone.utc)
    
    if dry_run:
        print(f"DRY RUN MODE - Starting iteration at {run_timestamp}")
        print("  No database writes or blockchain updates will be performed")
    else:
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
    current_totals = count_predictions_by_address(predictions)
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

    if dry_run:
        print("\nDRY RUN: Would store iteration in database")
        print(f"  - Run timestamp: {run_timestamp}")
        print(f"  - Predictions count: {len(predictions)}")
        print(f"  - Address deltas count: {len(address_deltas)}")
        print(f"  - Address totals count: {len(current_totals)}")
    else:
        # Store iteration in database
        iteration = db_service.store_iteration(
            run_timestamp=run_timestamp,
            predictions=predictions,
            address_deltas=address_deltas,
            address_totals=current_totals,
        )
        print(f"Stored iteration {iteration.id} in database")

    # Track finder status (active/inactive based on curated permissions)
    print("Tracking finder status...")
    curated_finders = get_curated_permission_recipients()
    
    if dry_run:
        print("\nDRY RUN: Would track finder status")
        print(f"  - Curated finders: {len(curated_finders)}")
        print(f"  - Active this iteration: {len(current_totals)}")
        _iteration_id = "DRY_RUN"
    else:
        db_service.track_finder_status(
            iteration_id=iteration.id,
            active_finder_keys={
                check_ss58_address(key) for key in current_totals.keys()
            },
            curated_permission_keys=curated_finders,
        )
        print(
            f"Tracked {len(curated_finders)} curated finders, {len(current_totals)} active this iteration"
        )
        _iteration_id = iteration.id

    # Calculate and display latest scores if evaluation sessions exist
    display_latest_scores(address_deltas)
    
    # Update stream permission weights on blockchain
    final_scores = get_final_scores(address_deltas)
    if final_scores:
        if dry_run:
            print("\nDRY RUN: Would update stream permission weights")
            print("  Final scores that would be set:")
            for address, score in sorted(
                final_scores.items(), key=lambda x: x[1], reverse=True
            )[:5]:  # Show top 5
                print(f"    {address[:8]}...{address[-6:]}: {score}")
            if len(final_scores) > 5:
                print(f"    ... and {len(final_scores) - 5} more addresses")
        else:
            print("Updating stream permission weights...")
            success = update_curated_permission_weights(final_scores)
            if success:
                print("Stream permission weights updated successfully")
            else:
                print("Failed to update stream permission weights")
    else:
        print("No final scores available - skipping stream weight update")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract predictions and update scores")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Perform a dry run (read only, no database writes or blockchain updates)"
    )
    
    args = parser.parse_args()
    
    while True:
        run_iteration(dry_run=args.dry_run)
        sleep(CONFIG.EXTRACTION_ITERATION_SLEEP)
