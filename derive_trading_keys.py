import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

load_dotenv()

def derive_trading_keys():
    print("🔑 Polymarket TRADING Key Deriver")
    print("---------------------------------")
    print("This creates keys for TRADING (not Builder Keys).\n")

    pk = (os.getenv("PRIVATE_KEY") or "").strip()
    proxy = (os.getenv("POLY_PROXY_ADDRESS") or "").strip()
    
    if not pk:
        print("❌ PRIVATE_KEY not found in .env")
        return
    if not proxy:
        print("❌ POLY_PROXY_ADDRESS not found in .env")
        return

    try:
        # L1 Client (No creds yet - we are deriving them!)
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=pk,
            chain_id=POLYGON,
            funder=proxy,
            signature_type=1  # Magic Link / Email Wallet
        )
        
        print("✓ L1 Authenticated.")
        print("⏳ Deriving Trading API Keys...")
        
        # derive_api_key returns ApiCreds object with attributes
        creds = client.derive_api_key()
        
        print("\n✅ SUCCESS! Replace your .env values with:\n")
        print(f'POLY_API_KEY="{creds.api_key}"')
        print(f'POLY_API_SECRET="{creds.api_secret}"')
        print(f'POLY_API_PASSPHRASE="{creds.api_passphrase}"')
        print("\n---------------------------------")
        print("Now run verify_auth.py again!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    derive_trading_keys()
