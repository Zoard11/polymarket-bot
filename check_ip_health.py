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
        # Test 1: GET (Scanning)
        url_get = "https://clob.polymarket.com/book?token_id=1"
        resp_get = requests.get(url_get, headers=headers, timeout=10)
        print(f"📡 GET TEST (Scanning): Status {resp_get.status_code}")
        
        # Test 2: POST (Trading)
        # We send a dummy post to the order endpoint to see if the WAF triggers
        url_post = "https://clob.polymarket.com/order"
        resp_post = requests.post(url_post, headers=headers, json={"test":True}, timeout=10)
        print(f"📡 POST TEST (Trading): Status {resp_post.status_code}")

        if resp_post.status_code == 403:
            print("\n❌ VERDICT: Cloudflare is specifically blocking POST (Trading) requests from this IP.")
            print("   (GET/Scanning is still allowed which is why you see opportunities).")
        elif resp_get.status_code == 403:
            print("\n❌ VERDICT: Your IP is COMPLETELY BLOCKED (Both GET and POST).")
        else:
            print("\n✅ VERDICT: Your IP appears clean to the WAF. (Unexpected result given the logs).")
            
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
