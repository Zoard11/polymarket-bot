import requests
import json
import os
from dotenv import load_dotenv

def test_ip_health():
    load_dotenv()
    url = "https://clob.polymarket.com/book?token_id=21742484370710649539304383416410403714521743048924080186523956424911046927508"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"🔍 Testing IP Health for: {url}")
    print(f"🛠️ Using User-Agent: {headers['User-Agent']}")
    
    try:
        # Test without proxy first
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"📡 Result (No Proxy): {resp.status_code}")
        if resp.status_code == 403:
            print("❌ STatus 403: Your IP is still HARD BLOCKED by Cloudflare.")
        elif resp.status_code == 200:
            print("✅ Status 200: Your IP is CLEAN (at least for GET requests).")
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
