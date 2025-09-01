import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from .database import database
from .models import (
    AddressPredictionCount,
    EvaluationSession,
    PredictionEvaluation,
    ProgramIteration,
)
from ..schemas import Prediction


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

    # Evaluation methods

    def get_last_evaluation_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the most recent completed evaluation."""
        with self.db.get_session() as session:
            session_result = (
                session.query(EvaluationSession)
                .filter(EvaluationSession.completed_at.is_not(None))
                .order_by(EvaluationSession.completed_at.desc())
                .first()
            )
            return session_result.completed_at if session_result else None

    def create_evaluation_session(
        self, evaluator_name: str
    ) -> EvaluationSession:
        """Create a new evaluation session."""
        with self.db.get_session() as session:
            evaluation_session = EvaluationSession(
                evaluator_name=evaluator_name,
                started_at=datetime.now(timezone.utc),
            )
            session.add(evaluation_session)
            session.commit()
            session.refresh(evaluation_session)
            return evaluation_session

    def store_evaluation(
        self,
        session_id: int,
        prediction_id: int,
        prediction_text: str,
        score: int,
    ) -> PredictionEvaluation:
        """Store a single prediction evaluation."""
        with self.db.get_session() as session:
            evaluation = PredictionEvaluation(
                session_id=session_id,
                prediction_id=prediction_id,
                prediction_text=prediction_text,
                score=score,
                evaluated_at=datetime.now(timezone.utc),
            )
            session.add(evaluation)
            session.commit()
            session.refresh(evaluation)
            return evaluation

    def complete_evaluation_session(self, session_id: int) -> None:
        """Mark an evaluation session as completed."""
        with self.db.get_session() as session:
            evaluation_session = (
                session.query(EvaluationSession)
                .filter(EvaluationSession.id == session_id)
                .first()
            )
            if evaluation_session:
                evaluation_session.completed_at = datetime.now(timezone.utc)
                session.commit()

    def get_evaluated_prediction_ids(self) -> Set[int]:
        """Get set of all prediction IDs that have already been evaluated."""
        with self.db.get_session() as session:
            results = session.query(PredictionEvaluation.prediction_id).all()
            return {result[0] for result in results}

    def sample_predictions_for_evaluation(
        self, predictions: List[Prediction], sample_size_per_address: int
    ) -> List[Prediction]:
        """
        Sample predictions for evaluation fairly across all addresses.
        Each address gets up to sample_size_per_address predictions evaluated.

        Args:
            predictions: List of predictions to sample from
            sample_size_per_address: Number of predictions to sample per address

        Returns:
            List of sampled predictions (fair distribution across addresses)
        """
        # Get already evaluated prediction IDs
        evaluated_ids = self.get_evaluated_prediction_ids()

        # Filter out already evaluated predictions
        unevaluated = [p for p in predictions if p.id not in evaluated_ids]

        if not unevaluated:
            return []

        # Group predictions by address
        predictions_by_address: Dict[str, List[Prediction]] = defaultdict(list)
        for prediction in unevaluated:
            predictions_by_address[prediction.inserted_by_address].append(
                prediction
            )

        # Sample from each address fairly
        sampled_predictions: List[Prediction] = []
        for _, addr_predictions in predictions_by_address.items():
            # Sample up to sample_size_per_address from this address
            actual_sample_size = min(
                sample_size_per_address, len(addr_predictions)
            )
            if actual_sample_size > 0:
                sampled = random.sample(addr_predictions, actual_sample_size)
                sampled_predictions.extend(sampled)

        # Shuffle the final list to avoid address-based ordering
        random.shuffle(sampled_predictions)
        return sampled_predictions

    def get_evaluation_stats(self) -> Dict[str, int]:
        """Get evaluation statistics."""
        with self.db.get_session() as session:
            total_evaluations = session.query(PredictionEvaluation).count()
            completed_sessions = (
                session.query(EvaluationSession)
                .filter(EvaluationSession.completed_at.is_not(None))
                .count()
            )

            if total_evaluations > 0:
                avg_score = session.query(
                    session.query(PredictionEvaluation.score).subquery().c.score
                ).scalar()
                # Get actual average
                scores = session.query(PredictionEvaluation.score).all()
                avg_score = (
                    sum(s[0] for s in scores) / len(scores) if scores else 0
                )
            else:
                avg_score = 0

            return {
                "total_evaluations": total_evaluations,
                "completed_sessions": completed_sessions,
                "average_score": int(round(avg_score, 1)),
            }


# Global service instance
db_service = DatabaseService()
