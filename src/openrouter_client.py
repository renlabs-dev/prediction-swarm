"""OpenRouter client for AI-powered prediction evaluation."""

import json
from typing import Literal, Optional, Union

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .config import CONFIG
from .schemas import Prediction


class LLMEvaluationResponse(BaseModel):
    """Pydantic model for LLM evaluation response."""

    score: Union[int, Literal["INVALID"]]
    reason: Optional[str] = None


class OpenRouterClient:
    """Client for evaluating predictions using OpenRouter AI models."""

    def __init__(self) -> None:
        """Initialize the OpenRouter client."""
        if not CONFIG.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment variables"
            )

        self.client = OpenAI(
            api_key=CONFIG.OPENROUTER_API_KEY,
            base_url=CONFIG.OPENROUTER_BASE_URL,
        )
        self.model = CONFIG.OPENROUTER_MODEL

    def evaluate_prediction(self, prediction: Prediction) -> Optional[int]:
        """Evaluate a single prediction and return a score 0-100.

        Args:
            prediction: The prediction to evaluate

        Returns:
            Integer score 0-100, or None if evaluation fails
        """
        try:
            # Format prediction for evaluation
            prediction_text = self._format_prediction_for_evaluation(prediction)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": CONFIG.AI_EVALUATION_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prediction_text},
                ],
                max_tokens=100,
                temperature=0.1,  # Low temperature for consistent scoring
            )

            if not response.choices or not response.choices[0].message.content:
                return None

            # Extract score from response
            score_text = response.choices[0].message.content.strip()
            return self._extract_score_from_response(score_text)

        except Exception as e:
            print(f"Error evaluating prediction {prediction.id}: {e}")
            return None

    def evaluate_prediction_full(
        self, prediction: Prediction
    ) -> Optional[LLMEvaluationResponse]:
        """Evaluate a single prediction and return the full response.

        Args:
            prediction: The prediction to evaluate

        Returns:
            LLMEvaluationResponse with score and reason, or None if evaluation fails
        """
        try:
            # Format prediction for evaluation
            prediction_text = self._format_prediction_for_evaluation(prediction)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": CONFIG.AI_EVALUATION_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prediction_text},
                ],
                max_tokens=200,  # Increased for reason field
                temperature=0.1,  # Low temperature for consistent scoring
            )

            if not response.choices or not response.choices[0].message.content:
                return None

            # Parse response as structured data
            response_text = response.choices[0].message.content.strip()
            return self._parse_full_response(response_text)

        except Exception as e:
            print(f"Error evaluating prediction {prediction.id}: {e}")
            return None

    def _format_prediction_for_evaluation(self, prediction: Prediction) -> str:
        """Format prediction data for AI evaluation.

        Args:
            prediction: The prediction to format

        Returns:
            Formatted text for evaluation
        """
        formatted = f"PREDICTION: {prediction.prediction}\n"
        formatted += f"TOPIC: {prediction.topic}\n"
        formatted += f"POSTED: {prediction.prediction_timestamp}\n"

        if prediction.context:
            formatted += f"CONTEXT: {prediction.context}\n"

        if prediction.verification_claims:
            formatted += "VERIFICATION CLAIMS:\n"
            for i, claim in enumerate(prediction.verification_claims, 1):
                formatted += f"{i}. {claim}\n"

        formatted += f"SOURCE: {prediction.predictor_twitter_username}"

        return formatted

    def _extract_score_from_response(self, response_text: str) -> Optional[int]:
        """Extract integer score from AI response using Pydantic model.

        Args:
            response_text: The AI response text

        Returns:
            Integer score 0-100, CONFIG.EVALUATION_INVALID_SCORE for invalid, or None if extraction fails
        """
        try:
            response_model = LLMEvaluationResponse.model_validate(
                response_text.strip()
            )

            if response_model.score == "INVALID":
                if response_model.reason:
                    print(f"    Reason: {response_model.reason}")
                return CONFIG.EVALUATION_INVALID_SCORE
            else:
                # Clamp numeric score to valid range
                score = int(response_model.score)
                return max(0, min(100, score))

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"    Failed to parse JSON response: {e}")
            print(f"    Raw response: {response_text}")
            return None

    def _parse_full_response(
        self, response_text: str
    ) -> Optional[LLMEvaluationResponse]:
        """Parse the full LLM response into a structured format.

        Args:
            response_text: The AI response text

        Returns:
            LLMEvaluationResponse with score and reason, or None if parsing fails
        """
        try:
            json_data = json.loads(response_text.strip())
            return LLMEvaluationResponse.model_validate(json_data)

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"    Failed to parse full JSON response: {e}")
            print(f"    Raw response: {response_text}")
            return None

    def evaluate_predictions_batch(
        self, predictions: list[Prediction]
    ) -> dict[int, int]:
        """Evaluate multiple predictions and return scores.

        Args:
            predictions: List of predictions to evaluate

        Returns:
            Dictionary mapping prediction IDs to scores
        """
        results: dict[int, int] = {}

        for prediction in predictions:
            score = self.evaluate_prediction(prediction)
            if score is not None:
                results[prediction.id] = score
            else:
                print(f"Failed to evaluate prediction {prediction.id}")

        return results

    def test_connection(self) -> bool:
        """Test the OpenRouter connection with a simple request.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"Testing OpenRouter connection with model: {self.model}")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Say 'Hello' and nothing else."}
                ],
                max_tokens=10,
                temperature=0.1,
            )

            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                print(
                    f"✅ OpenRouter connection successful! Response: {content}"
                )
                return True
            else:
                print("❌ OpenRouter returned empty response")
                return False

        except Exception as e:
            print(f"❌ OpenRouter connection failed: {e}")
            return False


# Global client instance
openrouter_client = OpenRouterClient()
