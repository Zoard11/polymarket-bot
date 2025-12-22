import requests

# Kalshi Public API (Elections domain allows unauthenticated market data)
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2"

class KalshiClient:
    def __init__(self):
        self.session = requests.Session()

    def fetch_active_markets(self, limit=1000):
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
        """Fetch best YES and NO asks for a specific ticker."""
        url = f"{KALSHI_API_URL}/markets/{ticker}/orderbook"
        try:
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            ob = resp.json().get('orderbook', {})
            
            # Kalshi V2 returns 'yes' and 'no' lists of [price, size]
            # These are the ASK prices for the respective sides.
            yes_asks = ob.get('yes', [])
            no_asks = ob.get('no', [])
            
            # Best ask is the one with the lowest price
            best_yes_ask = min(yes_asks, key=lambda x: x[0]) if yes_asks else None
            best_no_ask = min(no_asks, key=lambda x: x[0]) if no_asks else None
            
            return {
                'yes_ask': best_yes_ask, # [price, size]
                'no_ask': best_no_ask    # [price, size]
            }
        except Exception:
            return None
