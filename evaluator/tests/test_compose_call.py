#!/usr/bin/env python3
"""Debug compose_call for update_stream_permission."""

from torusdk._common import get_node_url
from torusdk.key import Keypair
from torustrateinterface import SubstrateInterface
from src.config import CONFIG

def main():
    """Test compose_call directly."""
    print("Testing compose_call for update_stream_permission...")
    
    # Connect to substrate
    substrate = SubstrateInterface(
        url=get_node_url(use_testnet=CONFIG.use_testnet)
    )
    
    # Create keypair
    keypair = Keypair.create_from_mnemonic(CONFIG.swarm_evaluator_mnemonic)
    print(f"Using account: {keypair.ss58_address}")
    
    # Test different parameter formats
    # BoundedBTreeMap appears to be a single-field struct containing the actual map
    test_cases = [
        {
            "name": "Wrapped list of tuples (single-element list)",
            "params": {
                "permission_id": CONFIG.CURATED_PERMISSION,
                "new_recipients": [[("5DPgzkSAa9hmHiz7fwpZKegcWwxZPhw6tWFeL1wVuVvFxpb9", 85)]],
            }
        },
        {
            "name": "Wrapped list of tuples (single-element tuple)",
            "params": {
                "permission_id": CONFIG.CURATED_PERMISSION,
                "new_recipients": ([("5DPgzkSAa9hmHiz7fwpZKegcWwxZPhw6tWFeL1wVuVvFxpb9", 85)],),
            }
        },
        {
            "name": "Dict wrapped in list",
            "params": {
                "permission_id": CONFIG.CURATED_PERMISSION,
                "new_recipients": [{"5DPgzkSAa9hmHiz7fwpZKegcWwxZPhw6tWFeL1wVuVvFxpb9": 85}],
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTrying: {test_case['name']}")
        print(f"Params: {test_case['params']}")
        
        try:
            call = substrate.compose_call(
                call_module="Permission0",
                call_function="update_stream_permission",
                call_params=test_case['params']
            )
            print(f"✓ Success! Call created: {call}")
            
            # Try to create an extrinsic with it
            extrinsic = substrate.create_signed_extrinsic(
                call=call,
                keypair=keypair,
            )
            print(f"✓ Extrinsic created successfully")
            
        except Exception as e:
            print(f"✗ Failed: {e}")
            # Try to get more detail about the error
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    
    substrate.close()

if __name__ == "__main__":
    main()