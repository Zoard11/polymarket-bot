import requests
import json
import os
from dotenv import load_dotenv

def test_ip_health():
    load_dotenv()
    # Official Health Check Endpoint
    url = "https://clob.polymarket.com/health"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"🔍 Testing IP Health for: {url}")
    print(f"🛠️ Using User-Agent: {headers['User-Agent']}")
    
    try:
        # Test: /book endpoint (This is where the bot got blocked on the VM)
        # Using a dummy ID to see if we get through the WAF
        url = "https://clob.polymarket.com/book?token_id=1"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"📡 WAF TEST (/book): Status {resp.status_code}")
        
        if resp.status_code == 403:
            print("❌ Status 403: Your IP is still HARD BLOCKED by Cloudflare.")
        elif resp.status_code in [200, 400, 404]:
            print("✅ Status Pass: Cloudflare is NOT blocking you (Server returned " + str(resp.status_code) + ").")
        else:
            print(f"❓ Unexpected Status: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

    # Test with proxy if environment variables are set
    proxy = os.getenv("HTTPS_PROXY")
    if proxy:
        print(f"\n🌐 Testing with PROXY: {proxy[:15]}...")
        try:
            proxies = {"https": proxy, "http": proxy}
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            print(f"📡 Result (With Proxy): {resp.status_code}")
            if resp.status_code == 200:
                print("✅ PROXY WORKS! Use this in your .env to bypass the block.")
        except Exception as e:
            print(f"❌ Proxy Test Failed: {e}")

if __name__ == "__main__":
    test_ip_health()
