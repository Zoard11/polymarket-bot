import requests
import time
import config

GAMMA_API_URL = "https://gamma-api.polymarket.com"

class PolyClient:
    def __init__(self):
        self.session = requests.Session()

    def _request_with_retries(self, url, params=None, timeout=10):
        for i in range(config.API_MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=timeout)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:
                    print(f"Rate limit (429) hit on {url}. Waiting 30s...")
                    time.sleep(30)
                else:
                    time.sleep(config.API_RETRY_DELAY)
            except Exception as e:
                time.sleep(config.API_RETRY_DELAY)
        return None

    def fetch_active_markets(self, min_volume=10000, limit=100):
        url = f"{GAMMA_API_URL}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "limit": 1000,
            "order_by": "volume24hr",
            "order_direction": "desc"
        }
        resp = self._request_with_retries(url, params=params)
        if resp:
            try:
                markets = resp.json()
                active = [m for m in markets if float(m.get('volume24hr', 0)) >= min_volume][:limit]
                return active
            except: pass
        return []

    def get_orderbook(self, market_id):
        url = f"{GAMMA_API_URL}/markets/{market_id}/orderbook"
        resp = self._request_with_retries(url, timeout=5)
        if resp:
            try: return resp.json()
            except: pass
        return None
