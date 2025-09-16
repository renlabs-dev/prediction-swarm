#!/usr/bin/env python3
"""Script to fetch data from memory API and save as CSV."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

import pandas as pd
from pydantic import BaseModel

from src.api_client import api_client
from src.config import MEMORY_URL


class Tweet(BaseModel):
    """Pydantic model for Tweet response from API."""
    
    id: int
    tweet_id: str
    full_text: str
    author_twitter_username: str
    author_twitter_user_id: Optional[str] = None
    tweet_timestamp: str
    tweet_type: str
    url: str
    inserted_by_address: str
    inserted_at: str
    conversation_id: Optional[str] = None
    in_reply_to_tweet_id: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    retweeted_tweet_id: Optional[str] = None
    raw_json: Optional[str] = None


def fetch_and_save_predictions(output_file: str = "predictions.csv") -> None:
    """Fetch the last 2000 predictions and save to CSV.

    Args:
        output_file: Path to output CSV file
    """
    print("Fetching predictions from memory API...")

    # Use a date far enough back to ensure we get 2000+ predictions
    # We'll limit to 2000 after fetching
    from_date = datetime(2025, 8, 1, tzinfo=timezone.utc)

    try:
        all_predictions = api_client.fetch_all_predictions(from_date)

        if not all_predictions:
            print("No predictions found.")
            return

        # Sort by ID descending and take the last 2000
        sorted_predictions = sorted(
            all_predictions, key=lambda p: p.id, reverse=True
        )
        latest_predictions = sorted_predictions[:2000]

        print(f"Selected {len(latest_predictions)} most recent predictions")

        # Convert to DataFrame
        prediction_data: List[Dict[str, Any]] = []
        for pred in latest_predictions:
            prediction_data.append(
                {
                    "id": pred.id,
                    "prediction": pred.prediction,
                    "full_post": pred.full_post,
                    "topic": pred.topic,
                    "predictor_twitter_username": pred.predictor_twitter_username,
                    "prediction_timestamp": pred.prediction_timestamp.isoformat(),
                    "url": pred.url,
                    "inserted_by_address": pred.inserted_by_address,
                    "context": pred.context or "",
                }
            )

        df = pd.DataFrame(prediction_data)

        # Save to CSV
        output_path = Path(output_file)
        df.to_csv(output_path, index=False)

        print(f"Saved {len(df)} predictions to {output_path.absolute()}")
        print(f"Columns: {list(df.columns)}")

    except Exception as e:
        print(f"Error fetching predictions: {e}")
        sys.exit(1)


def fetch_and_save_tweets(output_file: str = "tweets.csv", limit: int = 2000) -> None:
    """Fetch tweets from the /api/tweets/list endpoint and save to CSV.

    Args:
        output_file: Path to output CSV file
        limit: Number of tweets to fetch
    """
    print(f"Fetching {limit} tweets from memory API...")

    try:
        # Get authentication token
        session_token = api_client.get_session_token()
        headers = {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
        
        # Build the tweets API URL
        tweets_url = f"{MEMORY_URL.BASE}tweets/list"
        
        all_tweets: List[Tweet] = []
        offset = 0
        
        while len(all_tweets) < limit:
            batch_limit = min(1000, limit - len(all_tweets))
            
            # Parameters for the API call
            params = {
                "limit": batch_limit,
                "offset": offset,
                "sort_order": "desc",  # Get most recent first
            }
            
            print(f"Fetching tweets {offset}-{offset + batch_limit}...")
            
            response = requests.get(tweets_url, params=params, headers=headers)
            response.raise_for_status()
            
            tweets_batch_json = response.json()
            
            if not tweets_batch_json:
                print("No more tweets available")
                break
            
            # Parse with Pydantic
            tweets_batch = [Tweet.model_validate(tweet_data) for tweet_data in tweets_batch_json]
            all_tweets.extend(tweets_batch)
            offset += len(tweets_batch)
            
            if len(tweets_batch) < batch_limit:
                print("Reached end of available tweets")
                break

        print(f"Fetched {len(all_tweets)} tweets")

        if not all_tweets:
            print("No tweets found.")
            return

        # Convert to DataFrame using Pydantic models
        tweet_data: List[Dict[str, Any]] = []
        for tweet in all_tweets:
            tweet_data.append(tweet.model_dump())

        df = pd.DataFrame(tweet_data)

        # Save to CSV
        output_path = Path(output_file)
        df.to_csv(output_path, index=False)

        print(f"Saved {len(df)} tweets to {output_path.absolute()}")
        print(f"Columns: {list(df.columns)}")

    except Exception as e:
        print(f"Error fetching tweets: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_predictions_csv.py predictions [output_file]")
        print("  python fetch_predictions_csv.py tweets [output_file] [limit]")
        print()
        print("Examples:")
        print("  python fetch_predictions_csv.py predictions")
        print("  python fetch_predictions_csv.py predictions my_predictions.csv")
        print("  python fetch_predictions_csv.py tweets")
        print("  python fetch_predictions_csv.py tweets my_tweets.csv 5000")
        sys.exit(1)
    
    endpoint_type = sys.argv[1].lower()
    
    if endpoint_type == "predictions":
        output_file = sys.argv[2] if len(sys.argv) > 2 else "predictions.csv"
        fetch_and_save_predictions(output_file)
    elif endpoint_type == "tweets":
        output_file = sys.argv[2] if len(sys.argv) > 2 else "tweets.csv"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
        fetch_and_save_tweets(output_file, limit)
    else:
        print(f"Unknown endpoint type: {endpoint_type}")
        print("Use 'predictions' or 'tweets'")
        sys.exit(1)


if __name__ == "__main__":
    main()
