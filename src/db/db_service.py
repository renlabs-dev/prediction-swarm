import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, TypedDict

from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)

from ..schemas import Prediction
from .database import database
from .models import (
    AddressPredictionCount,
    EvaluationSession,
    FinalScore,
    Finder,
    PredictionEvaluation,
    ProgramIteration,
)


class FinderScores(TypedDict):
    """Type definition for finder scores data structure."""

    valid_scores: List[int]
    invalid_count: int


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
        finder_key: Ss58Address,
        score: int,
        full_text: Optional[str] = None,
        score_reason: Optional[str] = None,
    ) -> PredictionEvaluation:
        """Store a single prediction evaluation."""
        with self.db.get_session() as session:
            evaluation = PredictionEvaluation(
                session_id=session_id,
                prediction_id=prediction_id,
                prediction_text=prediction_text,
                finder_key=finder_key,
                score=score,
                full_text=full_text,
                score_reason=score_reason,
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

    # Normalized scoring with penalties methods

    def calculate_penalty(self, k: int, P: float, r: float) -> float:
        """Calculate escalating penalty based on invalid count.

        Args:
            k: Number of invalid predictions (strike count)
            P: Base penalty magnitude
            r: Escalation factor

        Returns:
            Penalty value to subtract from normalized score
        """
        if r == 1.0:
            return P * k
        else:
            return P * (r**k - 1) / (r - 1)

    def get_last_session_scores(
        self,
    ) -> Optional[Tuple[int, Dict[Ss58Address, FinderScores]]]:
        """Get scores from the last completed evaluation session grouped by finder_key.

        Returns:
            Tuple of (session_id, finder_scores_dict) where finder_scores_dict contains:
            {
                'finder_address': {
                    'valid_scores': [score1, score2, ...],
                    'invalid_count': count
                }
            }
        """
        with self.db.get_session() as session:
            # Get the last completed session
            last_session = (
                session.query(EvaluationSession)
                .filter(EvaluationSession.completed_at.is_not(None))
                .order_by(EvaluationSession.completed_at.desc())
                .first()
            )

            if not last_session:
                return None

            # Get all evaluations for that session
            evaluations = (
                session.query(PredictionEvaluation)
                .filter(PredictionEvaluation.session_id == last_session.id)
                .all()
            )

            # Group by finder_key
            finder_scores: Dict[Ss58Address, FinderScores] = defaultdict(
                lambda: {"valid_scores": [], "invalid_count": 0}
            )

            from ..config import CONFIG

            for eval_record in evaluations:
                finder_key = eval_record.finder_key
                score = eval_record.score

                if score == CONFIG.EVALUATION_INVALID_SCORE:
                    finder_scores[finder_key]["invalid_count"] += 1
                else:
                    finder_scores[finder_key]["valid_scores"].append(score)

            return last_session.id, dict(finder_scores)

    def normalize_score(
        self, score: float, min_score: int, max_score: int
    ) -> float:
        """Normalize a score to 0-1 range."""
        return (score - min_score) / (max_score - min_score)

    def calculate_normalized_scores_with_penalties(
        self,
        curated_permission_keys: List[Ss58Address],
    ) -> Optional[Dict[Ss58Address, Dict[str, float]]]:
        """Calculate normalized scores with escalating invalid penalties for the last session.

        Returns:
            Dictionary mapping finder addresses to their scoring details:
            {
                'finder_address': {
                    'base_score': float,     # Normalized average of valid scores (0-1)
                    'invalid_count': int,    # Number of invalid predictions
                    'penalty': float,        # Applied penalty
                    'final_score': float     # Final score after penalty (0-1)
                }
            }
        """
        session_data = self.get_last_session_scores()
        if not session_data:
            return None

        _, finder_scores = session_data

        from ..config import CONFIG

        result: Dict[Ss58Address, Dict[str, float]] = {}

        for finder_key, data in finder_scores.items():
            valid_scores = data["valid_scores"]
            invalid_count = data["invalid_count"]

            # Calculate base normalized score from valid scores
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                base_score = self.normalize_score(
                    avg_score,
                    CONFIG.EVALUATION_MIN_SCORE,
                    CONFIG.EVALUATION_MAX_SCORE,
                )
            else:
                base_score = 0.0  # No valid scores

            # Calculate penalty for invalid predictions
            penalty = (
                self.calculate_penalty(
                    invalid_count,
                    CONFIG.PENALTY_BASE,
                    CONFIG.PENALTY_ESCALATION,
                )
                if invalid_count > 0
                else 0.0
            )

            # Apply penalty and bound final score
            final_score = max(0.0, min(1.0, base_score - penalty))

            result[finder_key] = {
                "base_score": base_score,
                "invalid_count": invalid_count,
                "penalty": penalty,
                "final_score": final_score,
            }

        # Add all curated permission keys, giving 0 scores to those not in results
        for key in curated_permission_keys:
            if key not in result:
                result[key] = {
                    "base_score": 0.0,
                    "invalid_count": 0,
                    "penalty": 0.0,
                    "final_score": 0.0,
                }

        # Normalize scores across all addresses so they sum to 1.0
        total_final_score = sum(data["final_score"] for data in result.values())
        
        if total_final_score > 0:
            for finder_key in result:
                original_final_score = result[finder_key]["final_score"]
                result[finder_key]["final_score"] = original_final_score / total_final_score
        
        return result

    def store_final_scores(
        self,
        session_id: int,
        final_scores_data: Dict[Ss58Address, Dict[str, float]]
    ) -> None:
        """Store final calculated scores for an evaluation session.
        
        Args:
            session_id: The evaluation session ID
            final_scores_data: Dict with quality_score and final_score for each finder
        """
        with self.db.get_session() as session:
            # Clear any existing final scores for this session
            session.query(FinalScore).filter(
                FinalScore.session_id == session_id
            ).delete()
            
            # Store new final scores
            for finder_key, data in final_scores_data.items():
                final_score = FinalScore(
                    session_id=session_id,
                    finder_key=finder_key,
                    quality_score=data["quality_score"],
                    final_score=data["final_score"],
                )
                session.add(final_score)
            
            session.commit()

    def track_finder_status(
        self, 
        iteration_id: int,
        active_finder_keys: Set[Ss58Address],
        curated_permission_keys: List[Ss58Address]
    ) -> None:
        """Track finder status based on current iteration activity and permissions.
        
        Args:
            iteration_id: Current iteration ID
            active_finder_keys: Set of finder keys who found predictions this iteration
            curated_permission_keys: List of all keys with curated permissions
        """
        with self.db.get_session() as session:
            # Convert to sets for easier operations
            active_keys = set(active_finder_keys)
            permission_keys = set(curated_permission_keys)
            
            # Get all existing finders
            existing_finders = {
                finder.finder_key: finder 
                for finder in session.query(Finder).all()
            }
            
            # Process all keys with current permissions
            for key in permission_keys:
                finder = existing_finders.get(key)
                
                if finder:
                    # Update existing finder
                    finder.has_permission = True
                    finder.active = key in active_keys
                    if key in active_keys:
                        finder.last_active_iteration_id = iteration_id
                else:
                    # Create new finder
                    finder = Finder(
                        finder_key=key,
                        has_permission=True,
                        active=key in active_keys,
                        last_active_iteration_id=iteration_id if key in active_keys else None
                    )
                    session.add(finder)
            
            # Process existing finders who lost permission
            for key, finder in existing_finders.items():
                if key not in permission_keys:
                    finder.has_permission = False
                    finder.active = False
            
            session.commit()


# Global service instance
db_service = DatabaseService()
