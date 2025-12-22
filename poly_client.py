import requests
import time
import json
import concurrent.futures
import config
from ws_client import poly_ws

GAMMA_API_URL = "https://gamma-api.polymarket.com"

CLOB_API_URL = "https://clob.polymarket.com"

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

    def get_orderbook(self, token_id):
        """Fetch orderbook for a specific token ID from CLOB REST API or WebSocket."""
        if config.WS_ENABLED and token_id in poly_ws.orderbooks:
            return poly_ws.orderbooks[token_id]
            
        url = f"{CLOB_API_URL}/book"
        params = {"token_id": token_id}
        resp = self._request_with_retries(url, params=params, timeout=5)
        if resp:
            try: 
                return resp.json()
            except: pass
        return None

    def get_market_orderbooks(self, market):
        """Fetch all orderbooks (YES/NO) for a given market object."""
        try:
            tids = market.get('clobTokenIds')
            if isinstance(tids, str):
                tids = json.loads(tids)
            
            if not tids: return None
            
            # Fetch in parallel for speed if multiple tokens
            obs = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(tids)) as executor:
                future_to_tid = {executor.submit(self.get_orderbook, tid): tid for tid in tids}
                for future in concurrent.futures.as_completed(future_to_tid):
                    tid = future_to_tid[future]
                    ob = future.result()
                    if ob: obs[tid] = ob
            
            if not obs: return None
            
            # Normalize to yes/no for scanners
            final_obs = {'tokens': obs}
            if len(tids) == 2:
                # Assuming first is YES, second is NO (standard for Polymarket binary)
                final_obs['yes'] = obs.get(tids[0])
                final_obs['no'] = obs.get(tids[1])
            
            return final_obs
        except: return None
