import requests
import json
import os
import time
from dotenv import load_dotenv

def test_ip_health(trials=5):
    load_dotenv()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"🔍 Testing IP Health (Running {trials} trials for average latency)...")
    
    latencies_get = []
    latencies_post = []
    status_codes_get = set()
    status_codes_post = set()

    for i in range(trials):
        try:
            # Test 1: GET (Scanning)
            url_get = "https://clob.polymarket.com/book?token_id=1"
            start_get = time.time()
            resp_get = requests.get(url_get, headers=headers, timeout=10)
            latency_get = (time.time() - start_get) * 1000
            latencies_get.append(latency_get)
            status_codes_get.add(resp_get.status_code)
            
            # Test 2: POST (Trading)
            url_post = "https://clob.polymarket.com/order"
            start_post = time.time()
            resp_post = requests.post(url_post, headers=headers, json={"test":True}, timeout=10)
            latency_post = (time.time() - start_post) * 1000
            latencies_post.append(latency_post)
            status_codes_post.add(resp_post.status_code)
            
            print(f"   Trial {i+1}: GET {resp_get.status_code} ({latency_get:.1f}ms) | POST {resp_post.status_code} ({latency_post:.1f}ms)")
            time.sleep(0.5) # Gap between trials

        except Exception as e:
            print(f"   Trial {i+1}: ❌ Error: {e}")

    if not latencies_get:
        print("❌ No successful trials.")
        return

    avg_get = sum(latencies_get) / len(latencies_get)
    avg_post = sum(latencies_post) / len(latencies_post)

    print(f"\n📊 --- FINAL RESULTS ---")
    print(f"🌐 Average GET Latency: {avg_get:.1f}ms")
    print(f"💸 Average POST Latency: {avg_post:.1f}ms")

    if 403 in status_codes_post:
        print("\n❌ VERDICT: BLOCKED. Your IP is still triggering the 403 WAF block.")
    elif 401 in status_codes_post or 200 in status_codes_post or 400 in status_codes_post:
        print("\n✅ VERDICT: CLEAN. Your home IP passed the WAF test (Status 401 means authentication reached).")
    else:
        print("\n❓ VERDICT: UNCERTAIN. Unexpected status codes detected.")

if __name__ == "__main__":
    test_ip_health(trials=5)

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
