import requests
import time
import config

class KalshiClient:
    def __init__(self):
        # Using public elections API as it's more stable for reading data without 401s
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.session = requests.Session()

    def _request_with_retries(self, url, params=None, timeout=10):
        for i in range(config.API_MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=timeout)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:
                    time.sleep(30)
                else:
                    time.sleep(config.API_RETRY_DELAY)
            except:
                time.sleep(config.API_RETRY_DELAY)
        return None

    def fetch_active_markets(self, limit=1000):
        url = f"{self.base_url}/markets"
        params = {"limit": limit, "status": "open"}
        resp = self._request_with_retries(url, params=params)
        if resp:
            try: return resp.json().get('markets', [])
            except: pass
        return []

    def get_market_orderbook(self, ticker):
        """Fetch v2 order book (depth) for a specific ticker."""
        url = f"{self.base_url}/markets/{ticker}/orderbook"
        resp = self._request_with_retries(url, timeout=5)
        if resp:
            try: return resp.json().get('orderbook', {})
            except: pass
        return None
