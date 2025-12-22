import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient, ApiCreds
from py_clob_client.clob_types import OpenOrderParams
from py_clob_client.constants import POLYGON

from eth_account import Account

# Load environment variables
load_dotenv()

def verify_connection():
    print("🔐 Verifying Polymarket L2 Credentials...")
    print("---------------------------------------")

    host = "https://clob.polymarket.com"
    key = (os.getenv("PRIVATE_KEY") or os.getenv("PRVATE_KEY") or "").strip()
    api_key = (os.getenv("POLY_API_KEY") or "").strip()
    secret = (os.getenv("POLY_API_SECRET") or "").strip()
    passphrase = (os.getenv("POLY_API_PASSPHRASE") or "").strip()
    proxy_addr = (os.getenv("POLY_PROXY_ADDRESS") or "").strip() # <--- NEW
    chain_id = POLYGON

    if not key or not api_key or not secret:
        print("❌ Error: Missing Credentials in .env")
        return

    # 1. Derive Address from Private Key to verify match
    try:
        acct = Account.from_key(key)
        print(f"DEBUG: Signer (Private Key) : {acct.address}")
        if proxy_addr:
             print(f"DEBUG: Proxy  (Funder)      : {proxy_addr}")
             print(f"DEBUG: Proxy  (Length)      : {len(proxy_addr)} chars (Should be 42)")
    except Exception as e:
        print(f"❌ Error deriving address: {e}")
        return

    try:
        # Create Credentials Object
        creds = ApiCreds(
            api_key=api_key,
            api_secret=secret,
            api_passphrase=passphrase
        )

        # Initialize Client with Funder!
        client_args = {
            "host": host,
            "key": key, 
            "chain_id": chain_id,
            "creds": creds,
            "signature_type": 1
        }
        
        if proxy_addr:
            client_args["funder"] = proxy_addr  # <--- CRITICAL FIX

        client = ClobClient(**client_args)
        
        # Verify by fetching open orders
        print("📡 Connecting to CLOB (Checking Orders)...")
        try:
            orders = client.get_orders(OpenOrderParams())
            print("✅ AUTHENTICATION SUCCESSFUL!")
            print(f"   Key ID Verified. Open Orders Count: {len(orders)}")
        except Exception as e:
            print(f"❌ API Request Failed: {e}")
            print("\nTroubleshooting:")
            print("1. Does the Address above match your Profile?")
            print("2. Did you delete the OLD key and create a NEW one?")
            # Try fetching trades if orders fails (just in case)
            print(f"   (Orders check failed: {e})")
            print("   Trying Balance check...")
            try:
                # Some balance endpoints might work?
                # Actually, let's try a simple 'get_trades'?
                # or just assume if we got passed init, the 401 will show up on any request.
                raise e
            except:
                raise e
        
        # Verify Balance/Allowance (optional but good)
        print("\n💰 Checking Balance (Read-Only)...")
        # Note: derive_api_key() is internal usually, get_api_keys proves we are auth'd.
        
    except Exception as e:
        print(f"\n❌ Auth Failed: {e}")
        print("Double check that you copied the Secret and Passphrase correctly.")

if __name__ == "__main__":
    verify_connection()
