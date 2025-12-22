import requests
import time

GAMMA_API_URL = "https://gamma-api.polymarket.com"

class PolyClient:
    def __init__(self):
        self.session = requests.Session()

    def fetch_active_markets(self, min_volume=10000, limit=100):
        url = f"{GAMMA_API_URL}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "limit": 1000, # Fetch more to filter by volume
            "order_by": "volume24hr",
            "order_direction": "desc"
        }
        try:
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                print("Rate limit (429) hit on Gamma API. Backing off...")
                time.sleep(30)
                return []
            resp.raise_for_status()
            markets = resp.json()
            # Filter by volume and limit
            active = [m for m in markets if float(m.get('volume24hr', 0)) >= min_volume][:limit]
            return active
        except Exception as e:
            print(f"Error fetching Polymarket markets: {e}")
            return []

    def get_orderbook(self, market_id):
        url = f"{GAMMA_API_URL}/markets/{market_id}/orderbook"
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 429:
                return None
            resp.raise_for_status()
            return resp.json()
        except:
            return None
