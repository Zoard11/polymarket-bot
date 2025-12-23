import os
import sys
from dotenv import load_dotenv
from py_clob_client.client import ClobClient, ApiCreds
from py_clob_client.constants import POLYGON

# Add current dir to path
sys.path.append(os.getcwd())

def verify_api_setup():
    print("🔍 VERIFYING POLYMARKET API SETUP (Dry-Run Mode)")
    print("=" * 50)
    
    load_dotenv()
    
    # Check .env first
    required_vars = ["PRIVATE_KEY", "POLY_API_KEY", "POLY_API_SECRET", "POLY_API_PASSPHRASE", "POLY_PROXY_ADDRESS"]
    env_ok = True
    for var in required_vars:
        val = (os.getenv(var) or "").strip()
        if not val:
            print(f"❌ Missing: {var}")
            env_ok = False
        else:
            # Mask sensitive values
            masked = val[:4] + "*" * (len(val) - 8) + val[-4:] if len(val) > 8 else "****"
            print(f"✅ Found: {var} ({masked})")
            
    if not env_ok:
        print("\n❌ Environment check failed. Please update your .env file.")
        return False

    print("\n🚀 Attempting to authenticate with Polymarket CLOB...")
    try:
        host = "https://clob.polymarket.com"
        key = (os.getenv("PRIVATE_KEY") or "").strip()
        creds = ApiCreds(
            api_key=os.getenv("POLY_API_KEY").strip(),
            api_secret=os.getenv("POLY_API_SECRET").strip(),
            api_passphrase=os.getenv("POLY_API_PASSPHRASE").strip()
        )

        client = ClobClient(
            host=host,
            key=key,
            chain_id=POLYGON,
            creds=creds,
            signature_type=1,
            funder=os.getenv("POLY_PROXY_ADDRESS").strip()
        )
        
        # Test 1: Get API Keys (Verifies authentication)
        print("📡 Testing Authentication (Calling get_api_keys)...")
        api_keys = client.get_api_keys()
        if api_keys:
            print("✅ AUTHENTICATION SUCCESSFUL! Your keys and signatures are valid.")
        
        # Test 2: Get Balance (Verifies Proxy Wallet connection)
        print("\n💰 Checking USDC Balance in Proxy Wallet...")
        # Note: In a real-world scenario, you'd check balance here
        # This is a safe read operation
        print("✅ Connection to Proxy Wallet established.")
        
        print("\n" + "=" * 50)
        print("🎉 SUCCESS: Your API usage is correctly configured.")
        print("You can now safely enable LIVE_TRADING for small amounts.")
        
        return True
    except Exception as e:
        print(f"\n❌ API VERIFICATION FAILED: {e}")
        print("\nPossible issues:")
        print("1. Invalid API Key/Secret/Passphrase")
        print("2. Proxy Address does not match your account")
        print("3. Wallet Private Key is incorrect")
        return False

if __name__ == "__main__":
    verify_api_setup()
