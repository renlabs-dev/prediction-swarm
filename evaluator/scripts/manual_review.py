#!/usr/bin/env python3
"""Script for manual review of low-confidence predictions."""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd


def get_confidence_threshold() -> float:
    """Get confidence threshold from user input.
    
    Returns:
        Confidence threshold percentage (0-100)
    """
    while True:
        try:
            threshold_input = input("Enter confidence threshold (default 40%): ").strip()
            if not threshold_input:
                return 40.0
            
            threshold = float(threshold_input.replace('%', ''))
            if 0 <= threshold <= 100:
                return threshold
            else:
                print("Threshold must be between 0 and 100")
        except ValueError:
            print("Please enter a valid number")


def display_prediction_for_review(row: pd.Series, current: int, total: int) -> None:
    """Display a prediction for manual review.
    
    Args:
        row: Pandas Series with prediction data
        current: Current prediction number
        total: Total number of predictions to review
    """
    print(f"\n{'='*80}")
    print(f"[{current}/{total}] Prediction ID: {row['id']} (Confidence: {row['confidence']}%)")
    print(f"{'='*80}")
    
    # Show LLM validation result
    llm_valid = row.get('is_valid', 'Unknown')
    print(f"LLM says: {'VALID' if llm_valid else 'INVALID'} (confidence: {row['confidence']}%)")
    print(f"{'-'*80}")
    
    # Show full post
    print("FULL POST:")
    print(f"{row['full_post']}")
    print(f"{'-'*80}")
    
    # Show extracted prediction
    print("EXTRACTED PREDICTION:")
    print(f"{row['prediction']}")
    print(f"{'-'*80}")
    
    # Show metadata
    print("METADATA:")
    print(f"Topic: {row['topic']}")
    print(f"Posted by: {row['predictor_twitter_username']}")
    print(f"Posted at: {row['prediction_timestamp']}")
    print(f"URL: {row['url']}")
    
    if pd.notna(row.get('context', '')) and row.get('context', ''):
        print(f"Context: {row['context']}")
    
    print(f"{'='*80}")


def get_manual_validation() -> Optional[bool]:
    """Get manual validation input from user.
    
    Returns:
        True for valid, False for invalid, None to quit
    """
    while True:
        user_input = input("Is this a valid prediction? (y/n/s/q): ").strip().lower()
        
        if user_input in ['y', 'yes', 'valid']:
            return True
        elif user_input in ['n', 'no', 'invalid']:
            return False
        elif user_input in ['s', 'skip']:
            return None  # Skip this one
        elif user_input in ['q', 'quit']:
            return None
        else:
            print("Please enter 'y' for valid, 'n' for invalid, 's' to skip, or 'q' to quit")


def save_progress(df: pd.DataFrame, output_file: str) -> None:
    """Save current progress to output file.
    
    Args:
        df: DataFrame with current progress
        output_file: Path to output file
    """
    output_path = Path(output_file)
    df.to_csv(output_path, index=False)


def manual_review_csv(input_file: str, output_file: str, confidence_threshold: Optional[float] = None) -> None:
    """Perform manual review of low-confidence predictions.
    
    Args:
        input_file: Path to input CSV file with validation results
        output_file: Path to output CSV file with manual reviews
        confidence_threshold: Confidence threshold for review (default: ask user)
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)
    
    # Check if output file already exists (resuming previous session)
    output_path = Path(output_file)
    if output_path.exists():
        print(f"Found existing output file: {output_path}")
        print("Loading previous progress...")
        df = pd.read_csv(output_path)
    else:
        print(f"Loading validated predictions from {input_path}")
        df = pd.read_csv(input_path)
    
    if len(df) == 0:
        print("No predictions found in CSV")
        return
    
    # Check required columns
    required_cols = ['id', 'prediction', 'full_post', 'is_valid', 'confidence']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Missing required columns: {missing_cols}")
        print("Please run the LLM validation script first.")
        sys.exit(1)
    
    print(f"Loaded {len(df)} predictions")
    
    # Get confidence threshold
    if confidence_threshold is None:
        confidence_threshold = get_confidence_threshold()
    
    print(f"Using confidence threshold: {confidence_threshold}%")
    
    # Add manual_validation column if not exists
    if 'manual_validation' not in df.columns:
        df['manual_validation'] = None
    
    # Filter for low-confidence predictions
    # Handle NaN values in confidence column
    low_confidence_mask = (df['confidence'].notna()) & (df['confidence'] < confidence_threshold)
    low_confidence_df = df[low_confidence_mask].copy()
    
    if len(low_confidence_df) == 0:
        print(f"No predictions found with confidence < {confidence_threshold}%")
        # Still save the original data with the new column
        save_progress(df, output_file)
        print(f"Original data saved to: {output_path.absolute()}")
        return
    
    # Separate unreviewed and already reviewed predictions
    unreviewed_mask = low_confidence_df['manual_validation'].isna()
    unreviewed_df = low_confidence_df[unreviewed_mask].copy()
    already_reviewed_df = low_confidence_df[~unreviewed_mask].copy()
    
    total_low_confidence = len(low_confidence_df)
    unreviewed_count = len(unreviewed_df)
    already_reviewed_count = len(already_reviewed_df)
    
    print(f"Found {total_low_confidence} predictions with confidence < {confidence_threshold}%")
    print(f"  - {unreviewed_count} unreviewed")
    print(f"  - {already_reviewed_count} already reviewed")
    
    if unreviewed_count == 0:
        print("All low-confidence predictions have already been reviewed!")
        print(f"Results are in: {output_path.absolute()}")
        return
    print("\nStarting manual review...")
    print("Instructions: 'y' = valid, 'n' = invalid, 's' = skip, 'q' = quit")
    print("Progress is automatically saved after each review.\n")
    
    reviewed_count = 0
    valid_count = 0
    invalid_count = 0
    skipped_count = 0
    
    # Create combined list: unreviewed first, then already reviewed
    review_order = []
    
    # Add unreviewed predictions first
    for _, row in unreviewed_df.iterrows():
        review_order.append((row, False))  # False = not yet reviewed
    
    # Add already reviewed predictions
    for _, row in already_reviewed_df.iterrows():
        review_order.append((row, True))   # True = already reviewed
    
    try:
        for idx, (row, was_reviewed) in enumerate(review_order, 1):
            # Notify when transitioning to already reviewed predictions
            if not was_reviewed and idx > unreviewed_count:
                print("\n" + "="*60)
                print("🔄 All unreviewed predictions completed!")
                print("Now showing previously reviewed predictions (you can skip or re-review)")
                print("="*60)
                was_reviewed = True
            
            # Show current status in header
            status = "[ALREADY REVIEWED]" if was_reviewed else "[NEW]"
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(review_order)}] {status} Prediction ID: {row['id']} (Confidence: {row['confidence']}%)")
            
            if was_reviewed:
                current_review = row.get('manual_validation')
                if pd.notna(current_review):
                    current_status = "VALID" if current_review else "INVALID"
                    print(f"Current manual review: {current_status}")
            
            print(f"{'='*80}")
            
            # Show LLM validation result
            llm_valid = row.get('is_valid', 'Unknown')
            print(f"LLM says: {'VALID' if llm_valid else 'INVALID'} (confidence: {row['confidence']}%)")
            print(f"{'-'*80}")
            
            # Show full post
            print("FULL POST:")
            print(f"{row['full_post']}")
            print(f"{'-'*80}")
            
            # Show extracted prediction
            print("EXTRACTED PREDICTION:")
            print(f"{row['prediction']}")
            print(f"{'-'*80}")
            
            # Show metadata
            print("METADATA:")
            print(f"Topic: {row['topic']}")
            print(f"Posted by: {row['predictor_twitter_username']}")
            print(f"Posted at: {row['prediction_timestamp']}")
            print(f"URL: {row['url']}")
            
            if pd.notna(row.get('context', '')) and row.get('context', ''):
                print(f"Context: {row['context']}")
            
            print(f"{'='*80}")
            
            manual_result = get_manual_validation()
            
            if manual_result is None:
                # Check if user wants to quit
                if input("Skip this prediction? (y/n): ").strip().lower() in ['n', 'no']:
                    print("Quitting review...")
                    break
                else:
                    skipped_count += 1
                    continue
            
            # Store manual validation result
            original_idx = row.name  # This is the original index in the full DataFrame
            df.at[original_idx, 'manual_validation'] = manual_result
            
            # Save progress immediately after each review
            save_progress(df, output_file)
            
            reviewed_count += 1
            if manual_result:
                valid_count += 1
                print("✅ Marked as VALID and saved")
            else:
                invalid_count += 1
                print("❌ Marked as INVALID and saved")
            
    except KeyboardInterrupt:
        print("\n\nReview interrupted by user.")
        print("Progress has been saved.")
    
    # Final save
    save_progress(df, output_file)
    
    # Show summary
    print(f"\n{'='*50}")
    print("Manual Review Summary:")
    print(f"Predictions reviewed: {reviewed_count}")
    print(f"Marked as valid: {valid_count}")
    print(f"Marked as invalid: {invalid_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Results saved to: {output_path.absolute()}")
    
    # Show agreement stats if we have manual reviews
    if reviewed_count > 0:
        reviewed_rows = df[df['manual_validation'].notna()]
        if len(reviewed_rows) > 0:
            agreement = (reviewed_rows['is_valid'] == reviewed_rows['manual_validation']).sum()
            agreement_pct = (agreement / len(reviewed_rows)) * 100
            print(f"LLM-Human agreement: {agreement}/{len(reviewed_rows)} ({agreement_pct:.1f}%)")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python manual_review.py <input_csv> [output_csv] [confidence_threshold]")
        print("  input_csv: Path to CSV file with LLM validation results")
        print("  output_csv: Path to output CSV file (default: reviewed_predictions.csv)")
        print("  confidence_threshold: Threshold for review, 0-100 (default: ask user)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "reviewed_predictions.csv"
    
    confidence_threshold = None
    if len(sys.argv) > 3:
        try:
            confidence_threshold = float(sys.argv[3])
            if not (0 <= confidence_threshold <= 100):
                print("Confidence threshold must be between 0 and 100")
                sys.exit(1)
        except ValueError:
            print("Invalid confidence threshold. Must be a number between 0 and 100")
            sys.exit(1)
    
    manual_review_csv(input_file, output_file, confidence_threshold)


if __name__ == "__main__":
    main()