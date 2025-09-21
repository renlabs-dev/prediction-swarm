#!/usr/bin/env python3
"""Simple test for stream permission weight updates."""

from src.stream_weights import update_curated_permission_weights
from src.config import CONFIG
from torusdk._common import get_node_url
from torusdk.client import TorusClient

# Test recipients with sample weights (address -> score mapping)
TEST_RECIPIENTS = {
    "5DPgzkSAa9hmHiz7fwpZKegcWwxZPhw6tWFeL1wVuVvFxpb9": 95,
    "5FUWX2rknWrPpMc4yBorfMnPPwJs9akNoN3Dmwzm6PyoJsSn": 70,
}


def main():
    """Test stream permission weight updates."""
    print("Testing stream permission weight updates...")
    print(f"Using permission ID: {CONFIG.CURATED_PERMISSION}")
    print(f"Test recipients: {TEST_RECIPIENTS}")
    print()

    # Let's inspect the metadata for the function
    print("Checking function metadata...")
    client = TorusClient(get_node_url(use_testnet=CONFIG.use_testnet))

    # Try a simpler approach - just try calling and see what happens
    # Get the call directly through the runtime
    with client.get_conn() as substrate:
        try:
            # Get the call definition
            runtime_call = substrate.get_runtime_call(  # type: ignore
                "Permission0", "update_stream_permission"
            )
            print(f"Found update_stream_permission call")
            print(f"Call definition: {runtime_call}")
        except Exception as e:
            print(f"Could not get call definition: {e}")

    print()
    # Let's try with explicit parameter format
    try:
        success = update_curated_permission_weights(TEST_RECIPIENTS)
    except Exception as e:
        print(f"Exception details: {e}")
        print(f"Exception type: {type(e)}")
        import traceback

        traceback.print_exc()
        success = False

    print()
    if success:
        print("Test passed: Weight update successful")
    else:
        print("Test failed: Weight update failed")


if __name__ == "__main__":
    main()
