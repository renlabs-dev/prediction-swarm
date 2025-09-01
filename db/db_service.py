from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from db.database import database
from db.models import AddressPredictionCount, ProgramIteration
from src.schemas import Prediction


class DatabaseService:
    """Service for database operations related to program iterations and predictions."""

    def __init__(self) -> None:
        self.db = database

    def get_last_iteration(self) -> Optional[ProgramIteration]:
        """Get the most recent program iteration."""
        with self.db.get_session() as session:
            return (
                session.query(ProgramIteration)
                .order_by(ProgramIteration.run_timestamp.desc())
                .first()
            )

    def get_last_run_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the last program run."""
        last_iteration = self.get_last_iteration()
        return last_iteration.run_timestamp if last_iteration else None

    def count_predictions_by_address(
        self, predictions: List[Prediction]
    ) -> Dict[str, int]:
        """Count predictions by wallet address."""
        counts: Dict[str, int] = defaultdict(int)
        for prediction in predictions:
            counts[prediction.inserted_by_address] += 1
        return dict(counts)

    def get_previous_address_totals(self) -> Dict[str, int]:
        """Get the total prediction counts for each address from the last iteration."""
        last_iteration = self.get_last_iteration()
        if not last_iteration:
            return {}

        with self.db.get_session() as session:
            address_counts = (
                session.query(AddressPredictionCount)
                .filter(
                    AddressPredictionCount.iteration_id == last_iteration.id
                )
                .all()
            )

            return {
                ac.wallet_address: ac.total_predictions for ac in address_counts
            }

    def calculate_address_deltas(
        self, current_totals: Dict[str, int], previous_totals: Dict[str, int]
    ) -> Dict[str, int]:
        """Calculate the difference in predictions since last run."""
        deltas: Dict[str, int] = {}

        for address, current_count in current_totals.items():
            previous_count = previous_totals.get(address, 0)
            delta = current_count - previous_count
            if delta > 0:  # Only track addresses with new predictions
                deltas[address] = delta

        return deltas

    def store_iteration(
        self,
        run_timestamp: datetime,
        predictions: List[Prediction],
        address_deltas: Dict[str, int],
        address_totals: Dict[str, int],
    ) -> ProgramIteration:
        """Store a program iteration with all associated data."""
        with self.db.get_session() as session:
            # Create the program iteration
            iteration = ProgramIteration(
                run_timestamp=run_timestamp,
                predictions_fetched=len(predictions),
            )
            session.add(iteration)
            session.flush()  # Get the ID

            # Create address prediction counts
            address_counts: List[AddressPredictionCount] = []
            for address, delta_count in address_deltas.items():
                total_count = address_totals.get(address, delta_count)
                address_count = AddressPredictionCount(
                    iteration_id=iteration.id,
                    wallet_address=address,
                    prediction_count=delta_count,
                    total_predictions=total_count,
                )
                address_counts.append(address_count)

            session.add_all(address_counts)
            session.commit()

            return iteration

    def get_iterations_summary(self, limit: int = 10) -> List[ProgramIteration]:
        """Get recent program iterations with their data."""
        with self.db.get_session() as session:
            return (
                session.query(ProgramIteration)
                .order_by(ProgramIteration.run_timestamp.desc())
                .limit(limit)
                .all()
            )


# Global service instance
db_service = DatabaseService()
