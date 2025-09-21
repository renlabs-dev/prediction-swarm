"""Module for updating stream permission weights on blockchain."""

from typing import Dict, Optional

from torusdk._common import get_node_url
from torusdk.client import TorusClient
from torusdk.key import Keypair
from torusdk.types.types import Ss58Address

from .config import CONFIG


def update_curated_permission_weights(
    scores: Dict[Ss58Address, int], client: Optional[TorusClient] = None
) -> bool:
    """Update the recipient weights on the curated permission using calculated scores.

    Args:
        scores: Dict mapping addresses to final scores (0-100)
        client: Optional TorusClient instance. If None, creates a new one.

    Returns:
        True if successful, False if failed
    """
    if not scores:
        print("No scores to update - skipping stream weight update")
        return False

    if not CONFIG.swarm_evaluator_mnemonic:
        print(
            "SWARM_EVALUATOR_MNEMONIC not configured - cannot update stream weights"
        )
        return False

    # Create client if not provided
    if client is None:
        node = get_node_url(use_testnet=CONFIG.use_testnet)
        client = TorusClient(node)

    try:
        # Create keypair from mnemonic
        keypair = Keypair.create_from_mnemonic(CONFIG.swarm_evaluator_mnemonic)
        print(f"Using swarm evaluator account: {keypair.ss58_address}")

        # Convert scores to list of tuples format for BTreeMap
        recipients = [(address, weight) for address, weight in scores.items()]

        print(
            f"Updating stream permission weights for {len(recipients)} addresses..."
        )
        print(f"Permission ID: {CONFIG.CURATED_PERMISSION}")

        # Check if we need to wrap the recipients for BoundedBTreeMap encoding
        # When there are multiple entries, the SDK might expect them wrapped
        if len(recipients) > 1:
            print(f"DEBUG: Multiple recipients detected, may need special handling")
        
        # Pass all parameters explicitly, with None for those not being updated
        params_dict = {
            "permission_id": CONFIG.CURATED_PERMISSION,
            "new_recipients": recipients,  # Try passing as-is first
            "new_streams": None,
            "new_distribution_control": None,
            "new_recipient_manager": None,
            "new_weight_setter": None,
        }
        
        print(f"Debug - params being passed: {params_dict}")
        print(f"Debug - recipients type: {type(recipients)}")
        print(f"Debug - recipients content: {recipients}")
        
        try:
            response = client.compose_call(
                fn="update_stream_permission",
                params=params_dict,
                key=keypair,
                module="Permission0",
            )
        except Exception as inner_e:
            import traceback
            print(f"Inner error during compose_call: {inner_e}")
            print("Full traceback:")
            traceback.print_exc()
            raise

        print("Stream permission weights updated successfully!")
        print(f"Transaction hash: {response.extrinsic_hash}")

        # Log the weight updates
        for address, weight in recipients:
            print(f"  {address}: {weight}")

        return True

    except Exception as e:
        print(f"Failed to update stream permission weights: {e}")
        return False


def validate_stream_weight_config() -> bool:
    """Validate that required configuration is available for stream weight updates.

    Returns:
        True if configuration is valid, False otherwise
    """
    if not CONFIG.swarm_evaluator_mnemonic:
        print("Missing SWARM_EVALUATOR_MNEMONIC environment variable")
        return False

    if not CONFIG.CURATED_PERMISSION:
        print("Missing CURATED_PERMISSION configuration")
        return False

    return True
