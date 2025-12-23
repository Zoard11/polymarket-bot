try:
    from curl_cffi import requests
    print("✅ curl_cffi is installed!")
except ImportError:
    print("❌ curl_cffi is NOT installed. You need to run: pip install curl-cffi")
    exit(1)

def test_impersonate():
    url_get = "https://clob.polymarket.com/health"
    url_post = "https://clob.polymarket.com/order"
    
    print(f"🔍 Testing curl_cffi Impersonation (Chrome 120)...")
    
    try:
        # GET TEST
        resp_get = requests.get(url_get, impersonate="chrome120", timeout=10)
        print(f"📡 GET Status: {resp_get.status_code}")
        
        # POST TEST (Dummy)
        resp_post = requests.post(url_post, impersonate="chrome120", json={"test":True}, timeout=10)
        print(f"📡 POST Status: {resp_post.status_code}")
        
        if resp_get.status_code == 200 or resp_get.status_code == 404:
            if resp_post.status_code != 403:
                print("\n🎉 SUCCESS! curl-cffi bypassed the Cloudflare 403 block.")
                print("We can now use this to fix the bot without a proxy.")
            else:
                print("\n❌ FAILED: Still getting 403 on POST. This means your IP itself is blacklisted.")
        else:
            print("\n❌ FAILED: Unexpected status codes.")

    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_impersonate()
