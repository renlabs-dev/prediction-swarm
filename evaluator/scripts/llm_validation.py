#!/usr/bin/env python3
"""Script to validate predictions using LLM with modified prompt for validity and confidence."""

import json
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from src.config import CONFIG


class ValidationResponse(BaseModel):
    """Pydantic model for LLM validation response."""

    is_valid: bool
    confidence: int  # 0-100


class LLMValidator:
    """LLM client for prediction validation."""

    def __init__(self) -> None:
        """Initialize the LLM validator."""
        if not CONFIG.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment variables"
            )

        self.client = OpenAI(
            api_key=CONFIG.OPENROUTER_API_KEY,
            base_url=CONFIG.OPENROUTER_BASE_URL,
        )
        self.model = CONFIG.OPENROUTER_MODEL

        # Modified prompt for validity and confidence only
        self.validation_prompt = r"""
You evaluate predictions to determine if they are valid predictions and your confidence level.

VALIDITY GATE
A valid prediction is a verifiable claim about an uncertain future outcome that matters beyond those who control it.

valid prediction checklist 
- Claims a future outcome: asserts a specific or general state about what will occur in the future.
- Outcome is uncertain: The prediction is non-trivial and non-obvious.
- Outcome is verifiable in principle: an observer could examine future evidence and make a reasonable judgement whether the prediction held true, even if not with full precision or confidence.
- Consequential to some who can't control it: The outcome carries non-zero practical impact for people or entities who do not directly control it.

Conditional predictions ("if X then Y") are valid.

OUTPUT FORMAT
Return ONLY a valid JSON object. Do not include markdown code fences, backticks, or any other formatting.

{
    "is_valid": boolean,
    "confidence": int (0-100, where 100 = completely confident, 0 = completely uncertain)
}

Example outputs:
{"is_valid": true, "confidence": 85}
{"is_valid": false, "confidence": 95}
"""

    def validate_prediction(
        self, prediction_text: str, full_post: str, topic: str
    ) -> Optional[Tuple[bool, int]]:
        """Validate a prediction and return validity and confidence.

        Args:
            prediction_text: The extracted prediction
            full_post: The full post text
            topic: The prediction topic

        Returns:
            Tuple of (is_valid, confidence) or None if validation fails
        """
        try:
            formatted_text = f"PREDICTION: {prediction_text}\nTOPIC: {topic}\nFULL POST: {full_post}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.validation_prompt},
                    {"role": "user", "content": formatted_text},
                ],
                max_tokens=50,
                temperature=0.1,
            )

            if not response.choices or not response.choices[0].message.content:
                return None

            response_text = response.choices[0].message.content.strip()
            return self._parse_validation_response(response_text)

        except Exception as e:
            print(f"Error validating prediction: {e}")
            return None

    def _parse_validation_response(
        self, response_text: str
    ) -> Optional[Tuple[bool, int]]:
        """Parse the LLM validation response.

        Args:
            response_text: The raw response from LLM

        Returns:
            Tuple of (is_valid, confidence) or None if parsing fails
        """
        try:
            json_data = json.loads(response_text.strip())
            validation = ValidationResponse.model_validate(json_data)
            return validation.is_valid, validation.confidence

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"Failed to parse validation response: {e}")
            print(f"Raw response: {response_text}")
            return None


def validate_predictions_csv(input_file: str, output_file: str) -> None:
    """Validate predictions from CSV and save results.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    print(f"Loading predictions from {input_path}")
    df = pd.read_csv(input_path)

    if len(df) == 0:
        print("No predictions found in CSV")
        return

    print(f"Loaded {len(df)} predictions")

    # Initialize validator
    try:
        validator = LLMValidator()
    except ValueError as e:
        print(f"Error initializing validator: {e}")
        sys.exit(1)

    # Add new columns
    df["is_valid"] = None
    df["confidence"] = None

    # Validate each prediction
    for idx, row in df.iterrows():
        print(f"Validating prediction {idx + 1}/{len(df)}: ID {row['id']}")

        result = validator.validate_prediction(
            str(row["prediction"]), str(row["full_post"]), str(row["topic"])
        )

        if result is not None:
            is_valid, confidence = result
            df.at[idx, "is_valid"] = is_valid
            df.at[idx, "confidence"] = confidence
            print(f"  Result: valid={is_valid}, confidence={confidence}%")
        else:
            print("  Validation failed - skipping")

    # Save results
    output_path = Path(output_file)
    df.to_csv(output_path, index=False)

    # Show summary
    valid_count = df["is_valid"].sum() if df["is_valid"].notna().any() else 0
    total_validated = df["is_valid"].notna().sum()
    avg_confidence = (
        df["confidence"].mean() if df["confidence"].notna().any() else 0
    )

    print(f"\nValidation Summary:")
    print(f"Total validated: {total_validated}/{len(df)}")
    print(f"Valid predictions: {valid_count}")
    print(f"Invalid predictions: {total_validated - valid_count}")
    print(f"Average confidence: {avg_confidence:.1f}%")
    print(f"Results saved to: {output_path.absolute()}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python llm_validation.py <input_csv> [output_csv]")
        print("  input_csv: Path to CSV file with predictions")
        print(
            "  output_csv: Path to output CSV file (default: validated_predictions.csv)"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = (
        sys.argv[2] if len(sys.argv) > 2 else "validated_predictions.csv"
    )

    validate_predictions_csv(input_file, output_file)


if __name__ == "__main__":
    main()
