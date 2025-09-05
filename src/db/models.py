from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)


class Base(DeclarativeBase):
    pass


class ProgramIteration(Base):
    """Tracks each time the program runs and fetches predictions."""

    __tablename__ = "program_iterations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the program iteration started",
    )
    predictions_fetched: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Total number of predictions fetched in this iteration",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When this record was created",
    )

    # Relationship to address prediction counts
    address_counts: Mapped[List["AddressPredictionCount"]] = relationship(
        "AddressPredictionCount",
        back_populates="iteration",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ProgramIteration(id={self.id}, "
            f"run_timestamp={self.run_timestamp}, "
            f"predictions_fetched={self.predictions_fetched})>"
        )


class AddressPredictionCount(Base):
    """Tracks prediction counts per wallet address for each program iteration."""

    __tablename__ = "address_prediction_counts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    iteration_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("program_iterations.id"),
        nullable=False,
        doc="Reference to the program iteration",
    )
    wallet_address: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="SS58 wallet address that inserted predictions",
    )
    prediction_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of predictions this address inserted since last run",
    )
    total_predictions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Total number of predictions this address has ever inserted",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When this record was created",
    )

    # Relationship back to iteration
    iteration: Mapped["ProgramIteration"] = relationship(
        "ProgramIteration", back_populates="address_counts"
    )

    def __repr__(self) -> str:
        return (
            f"<AddressPredictionCount(id={self.id}, "
            f"address={self.wallet_address[:8]}..., "
            f"count={self.prediction_count}, "
            f"total={self.total_predictions})>"
        )


class EvaluationSession(Base):
    """Tracks human evaluation sessions."""

    __tablename__ = "evaluation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluator_name: Mapped[str] = mapped_column(
        String, nullable=False, doc="Name of the person doing the evaluation"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the evaluation session started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the evaluation session was completed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When this record was created",
    )

    # Relationship to evaluations
    evaluations: Mapped[List["PredictionEvaluation"]] = relationship(
        "PredictionEvaluation",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationSession(id={self.id}, "
            f"evaluator={self.evaluator_name}, "
            f"started={self.started_at}, "
            f"completed={self.completed_at})>"
        )


class PredictionEvaluation(Base):
    """Stores human evaluations of predictions."""

    __tablename__ = "prediction_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("evaluation_sessions.id"),
        nullable=False,
        doc="Reference to the evaluation session",
    )
    prediction_id: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="The prediction ID from the API"
    )
    prediction_text: Mapped[str] = mapped_column(
        Text, nullable=False, doc="The actual prediction text being evaluated"
    )
    finder_key: Mapped[Ss58Address] = mapped_column(
        String,
        nullable=False,
        doc="SS58 wallet address of the finder who submitted the prediction",
    )
    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Human score from 0-100, or -999 for invalid predictions",
    )
    full_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Full prediction text from API (full_post field)",
    )
    score_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Reason provided by LLM for the score",
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When this prediction was evaluated",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When this record was created",
    )

    # Relationship back to session
    session: Mapped["EvaluationSession"] = relationship(
        "EvaluationSession", back_populates="evaluations"
    )

    def __repr__(self) -> str:
        return (
            f"<PredictionEvaluation(id={self.id}, "
            f"prediction_id={self.prediction_id}, "
            f"score={self.score})>"
        )


class FinalScore(Base):
    """Stores final calculated scores for each finder per evaluation session."""

    __tablename__ = "final_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("evaluation_sessions.id"),
        nullable=False,
        doc="Reference to the evaluation session",
    )
    finder_key: Mapped[Ss58Address] = mapped_column(
        String,
        nullable=False,
        doc="SS58 wallet address of the finder",
    )
    quality_score: Mapped[float] = mapped_column(
        nullable=False,
        doc="Quality score from evaluation (normalized across finders)",
    )
    final_score: Mapped[float] = mapped_column(
        nullable=False,
        doc="Final normalized score (share of total contribution)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When this record was created",
    )

    # Relationship back to session
    session: Mapped["EvaluationSession"] = relationship("EvaluationSession")

    def __repr__(self) -> str:
        return (
            f"<FinalScore(id={self.id}, "
            f"finder={self.finder_key[:8]}..., "
            f"final_score={self.final_score:.3f})>"
        )


class Finder(Base):
    """Tracks all finders with curated permissions and their active status."""

    __tablename__ = "finders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finder_key: Mapped[Ss58Address] = mapped_column(
        String,
        nullable=False,
        unique=True,
        doc="SS58 wallet address of the finder",
    )
    active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        doc="Whether this finder is currently active (has permission and finds predictions)",
    )
    has_permission: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        doc="Whether this finder currently has curated permission",
    )
    last_active_iteration_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("program_iterations.id"),
        nullable=True,
        doc="Last iteration where this finder submitted predictions",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When this finder was first discovered",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        doc="When this record was last updated",
    )

    # Relationship to last active iteration
    last_active_iteration: Mapped[Optional["ProgramIteration"]] = relationship(
        "ProgramIteration"
    )

    def __repr__(self) -> str:
        return (
            f"<Finder(id={self.id}, "
            f"finder={self.finder_key[:8]}..., "
            f"active={self.active}, "
            f"has_permission={self.has_permission})>"
        )
