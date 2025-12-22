import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# Load environment variables
load_dotenv()

def generate_keys():
    print("🔑 Polymarket L2 Key Generator")
    print("------------------------------")

    # Try both variable names (handling user typo)
    pk = os.getenv("PRIVATE_KEY") or os.getenv("POLY_PRIVATE_KEY")
    
    if not pk:
        print("❌ Error: Could not find Private Key in .env")
        print("Please ensure you set PRIVATE_KEY=0x... in your .env file.")
        return

    print("✓ Private Key found.")
    
    try:
        # Initialize Client with just Private Key (L1 Auth)
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=pk, 
            chain_id=POLYGON
        )

        print("✓ Authenticated with L1 Private Key.")
        print("⏳ Generating L2 API Credentials...")
        
        # Request new API Keys
        try:
            resp = client.create_api_key()
            
            print("\n✅ SUCCESS! COPY THESE VALUES TO YOUR .env FILE:\n")
            print(f"POLY_API_KEY={resp['apiKey']}")
            print(f"POLY_API_SECRET={resp['secret']}")
            print(f"POLY_API_PASSPHRASE={resp['passphrase']}")
            print("\n------------------------------")
            print("DO NOT SHARE THESE VALUES WITH ANYONE.")

        except Exception as e:
            if "400" in str(e) or "Could not create" in str(e):
                print("\n❌ EXISTING KEY FOUND")
                print("Polymarket only allows ONE API Key per account.")
                print("Since we don't have the old secret, we cannot delete it programmatically.")
                print("\n👉 ACTION REQUIRED: Go to Polymarket.com -> Settings -> API Keys and DELETE the existing key manually.")
                print("Then run this script again.")
            else:
                print(f"\n❌ Error generating keys: {e}")
        
    except Exception as e:
        print(f"\n❌ Error generating keys: {e}")
        print("Ensure your Private Key is correct and includes '0x' prefix if applicable.")

if __name__ == "__main__":
    generate_keys()
