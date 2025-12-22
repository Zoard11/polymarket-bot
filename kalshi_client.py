import requests

# Kalshi Public API (Elections domain allows unauthenticated market data)
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2"

class KalshiClient:
    def __init__(self):
        self.session = requests.Session()

    def fetch_active_markets(self, limit=100):
        """Fetch active markets from Kalshi."""
        url = f"{KALSHI_API_URL}/markets"
        params = {
            "limit": limit,
            "status": "open"
        }
        try:
            # Note: Public endpoints don't require auth for broad market lists
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get('markets', [])
        except Exception as e:
            print(f"Error fetching Kalshi markets: {e}")
            return []

    def get_market_orderbook(self, ticker):
        """Fetch orderbook for a specific ticker."""
        url = f"{KALSHI_API_URL}/markets/{ticker}/orderbook"
        try:
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json().get('orderbook', {})
        except Exception as e:
            # print(f"Error fetching Kalshi orderbook for {ticker}: {e}")
            return None
