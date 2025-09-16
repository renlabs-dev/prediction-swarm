from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
from torusdk.types.types import (  # pyright: ignore[reportMissingTypeStubs]
    Ss58Address,
)


class VerificationOutcome(str, Enum):
    NOT_MATURED = "NotMatured"
    MATURED_TRUE = "MaturedTrue"
    MATURED_FALSE = "MaturedFalse"
    MATURED_MOSTLY_TRUE = "MaturedMostlyTrue"
    UNVERIFIABLE = "Unverifiable"
    MISSING_CONTEXT = "MissingContext"


class VerificationClaim(BaseModel):
    id: int = Field(
        ..., description="Unique identifier for the verification claim"
    )
    inserted_at: datetime = Field(
        ..., description="Timestamp when the verification claim was inserted"
    )
    inserted_by_address: Ss58Address = Field(
        ...,
        description="Wallet address of the agent who inserted the verification claim",
    )
    outcome: VerificationOutcome = Field(
        ..., description="The outcome of the prediction verification process"
    )
    prediction_id: int = Field(
        ...,
        description="The ID of the prediction that this verification claim is for",
    )
    proof: str = Field(
        ...,
        description="The proof for the verification claim (markdown text containing data, links to sources, reasoning)",
    )


class VerificationVerdict(BaseModel):
    id: int = Field(
        ..., description="Unique identifier for the verification verdict"
    )
    inserted_at: datetime = Field(
        ..., description="Timestamp when the verification verdict was inserted"
    )
    inserted_by_address: Ss58Address = Field(
        ...,
        description="Wallet address of the agent who inserted the verification verdict",
    )
    prediction_id: int = Field(
        ...,
        description="The ID of the prediction that this verification verdict is for",
    )
    prediction_verification_claim_id: Optional[int] = Field(
        None,
        description="The ID of the verification claim that this verdict most agrees with",
    )
    reasoning: str = Field(
        ..., description="The reasoning for the verdict (markdown text)"
    )


class Prediction(BaseModel):
    id: int = Field(..., description="Unique identifier for the prediction")
    full_post: str = Field(
        ..., description="The full text of the post containing the prediction"
    )
    inserted_at: datetime = Field(
        ..., description="Timestamp when the prediction was inserted"
    )
    inserted_by_address: Ss58Address = Field(
        ...,
        description="Wallet address of the agent who inserted the prediction",
    )
    prediction: str = Field(
        ...,
        description="The prediction contained in the post (extracted verbatim from the post)",
    )
    prediction_timestamp: datetime = Field(
        ..., description="Timestamp when the prediction was made"
    )
    predictor_twitter_username: str = Field(
        ...,
        description="The Twitter username of the agent who made the prediction (without '@')",
    )
    topic: str = Field(..., description="The topic of the prediction")
    url: str = Field(
        ..., description="The URL of the post containing the prediction"
    )
    verification_claims: List[VerificationClaim] = Field(
        ..., description="The verification claims for the prediction"
    )

    context: Optional[str] = Field(
        None,
        description="Optional context for the post, e.g. if the tweet is a reply in a thread",
    )
    extended_data: str = Field(
        "", description="Extended data as JSON for schema-specific fields"
    )
    predictor_twitter_user_id: Optional[str] = Field(
        None, description="The Twitter ID of the user who made the prediction"
    )
    schema_id: str = Field("", description="Schema ID used for validation")
    verification_verdict: Optional[VerificationVerdict] = Field(
        None,
        description="The verdict for the prediction, based on all its verification claims",
    )


PredictionsList = List[Prediction]
