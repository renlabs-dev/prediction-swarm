#!/usr/bin/env python3
"""Script to validate predictions using LLM with modified prompt for validity and confidence."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from src.config import CONFIG


class ValidationResponse(BaseModel):
    """Pydantic model for LLM validation response."""

    is_valid: bool
    confidence: int  # 0-100


class LLMValidator:
    """Async LLM client for prediction validation."""

    def __init__(self) -> None:
        """Initialize the LLM validator."""
        if not CONFIG.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment variables"
            )

        self.client = AsyncOpenAI(
            api_key=CONFIG.OPENROUTER_API_KEY,
            base_url=CONFIG.OPENROUTER_BASE_URL,
        )
        self.model = CONFIG.OPENROUTER_MODEL

        # Use validation-only prompt from config
        self.validation_prompt = CONFIG.VALIDATION_ONLY_PROMPT

    async def validate_prediction(
        self, full_post: str, topic: str
    ) -> Optional[Tuple[bool, int]]:
        """Validate a prediction and return validity and confidence.

        Args:
            full_post: The full post text
            topic: The prediction topic

        Returns:
            Tuple of (is_valid, confidence) or None if validation fails
        """
        try:
            formatted_text = f"TOPIC: {topic}\nFULL POST: {full_post}"

            response = await self.client.chat.completions.create(
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

    print(f"Loading data from {input_path}")
    df = pd.read_csv(input_path)

    if len(df) == 0:
        print("No data found in CSV")
        return

    print(f"Loaded {len(df)} rows")

    # Detect format based on column headers
    columns = set(df.columns.str.lower())
    
    if 'prediction' in columns and 'full_post' in columns:
        # Predictions format
        print("Detected predictions format")
        get_full_post = lambda row: str(row["full_post"])
        get_topic = lambda row: str(row["topic"]) if "topic" in columns else "general"
    elif 'text' in columns:
        # Tweets format
        print("Detected tweets format")
        get_full_post = lambda row: str(row["text"])
        get_topic = lambda row: "general"  # tweets don't have topics
    else:
        raise ValueError(f"Unrecognized CSV format. Expected 'prediction'/'full_post' or 'text' columns. Found: {list(df.columns)}")

    # Initialize validator
    try:
        validator = LLMValidator()
    except ValueError as e:
        print(f"Error initializing validator: {e}")
        sys.exit(1)

    # Add new columns
    df["is_valid"] = None
    df["confidence"] = None

    # Process rows in parallel batches of 16
    async def process_batch(batch_rows: List[Tuple[int, pd.Series]]) -> List[Tuple[int, Optional[Tuple[bool, int]]]]:
        tasks = []
        for idx, row in batch_rows:
            full_post = get_full_post(row)
            topic = get_topic(row)
            task = validator.validate_prediction(full_post, topic)
            tasks.append((idx, task))
        
        # Actually run tasks in parallel using asyncio.gather
        task_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Pair results with indices
        results = []
        for i, (idx, _) in enumerate(tasks):
            result = task_results[i]
            if isinstance(result, Exception):
                print(f"Error in batch processing for row {idx}: {result}")
                results.append((idx, None))
            else:
                results.append((idx, result))
        return results

    async def validate_all_rows():
        batch_size = 16
        total_rows = len(df)
        total_batches = (total_rows + batch_size - 1) // batch_size
        
        for i in range(0, total_rows, batch_size):
            batch_end = min(i + batch_size, total_rows)
            batch_rows = [(idx, row) for idx, row in df.iloc[i:batch_end].iterrows()]
            batch_num = i // batch_size + 1
            
            print(f"Processing batch {batch_num}/{total_batches} (rows {i+1}-{batch_end}/{total_rows})")
            
            batch_results = await process_batch(batch_rows)
            
            # Count results for this batch
            valid_count = sum(1 for _, result in batch_results if result and result[0])
            failed_count = sum(1 for _, result in batch_results if result is None)
            
            for idx, result in batch_results:
                if result is not None:
                    is_valid, confidence = result
                    df.at[idx, "is_valid"] = is_valid
                    df.at[idx, "confidence"] = confidence
                else:
                    df.at[idx, "is_valid"] = False  # Mark failed validations as False
                    df.at[idx, "confidence"] = 0
            
            print(f"  Batch {batch_num} complete: {valid_count} valid, {len(batch_results)-valid_count-failed_count} invalid, {failed_count} failed")

    # Prepare output path
    output_path = Path(output_file)
    
    # Run async validation
    asyncio.run(validate_all_rows())

    # Save final results
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
