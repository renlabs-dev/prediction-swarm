from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
