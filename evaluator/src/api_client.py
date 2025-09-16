import json
from datetime import datetime
from typing import List

import requests
from torusdk.key import load_keypair

from .config import CONFIG, MEMORY_URL
from .schemas import Prediction


class APIClient:
    """Client for interacting with the Memory API."""

    def __init__(self) -> None:
        self._session_token: str | None = None

    def get_session_token(self) -> str:
        """Get authentication session token."""
        if self._session_token is not None:
            return self._session_token

        key = load_keypair("swarm-consumer")

        # Get challenge
        r = requests.post(
            MEMORY_URL.CHALLENGE,
            data=json.dumps({"wallet_address": key.ss58_address}),
            headers={"Content-Type": "application/json"},
        )
        if r.status_code != 200:
            print(f"Failed to get challenge: {r.status_code}")
            raise Exception("Error getting challenge")

        response_json = r.json()
        challenge_token: str = response_json["message"]
        signed_challenge = key.sign(challenge_token)

        # Verify challenge
        auth_response = requests.post(
            MEMORY_URL.VERIFY,
            data=json.dumps(
                {
                    "challenge_token": response_json["challenge_token"],
                    "signature": signed_challenge.hex(),
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        if auth_response.status_code != 200:
            print(f"Failed to verify signature: {auth_response.status_code}")
            raise Exception("Error verifying signature")

        auth = auth_response.json()
        self._session_token = str(auth["session_token"])
        return self._session_token

    def fetch_all_predictions(self, from_date: datetime) -> List[Prediction]:
        """
        Fetch all predictions since the given date using pagination.

        Args:
            from_date: Fetch predictions since this datetime (should be timezone-aware)

        Returns:
            List of all predictions since from_date
        """
        session_token = self.get_session_token()
        all_predictions: List[Prediction] = []
        offset = 0
        limit = CONFIG.PAGINATION_LIMIT

        # Convert datetime to RFC3339 format for API
        from_str = from_date.isoformat()

        print(f"Fetching predictions since {from_str}")

        while True:
            # Build query parameters
            params = {
                "from": from_str,
                "limit": str(limit),
                "offset": str(offset),
                "sort_by": "id",
                "sort_order": "asc",
            }

            # Make API request
            r = requests.get(
                MEMORY_URL.LIST_PREDICTIONS,
                params=params,
                headers={"Authorization": f"Bearer {session_token}"},
            )

            if r.status_code != 200:
                print(f"Failed to get predictions: {r.status_code}")
                raise Exception("Error getting predictions")

            # Parse predictions
            raw_data = r.json()
            page_predictions = [
                Prediction.model_validate(item) for item in raw_data
            ]
            all_predictions.extend(page_predictions)

            print(f"Fetched {len(all_predictions)} predictions so far...")

            # Check if we got a full page - if not, we're done
            if len(page_predictions) < limit:
                break

            offset += limit

        print(f"Finished fetching {len(all_predictions)} total predictions")
        return all_predictions


# Global API client instance
api_client = APIClient()
