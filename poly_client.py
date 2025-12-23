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
            "closed": "false",
            "limit": 1000,
            "order_by": "volume24hr",
            "order_direction": "desc"
        }
        resp = self._request_with_retries(url, params=params)
        if resp:
            try:
                markets = resp.json()
                # 1. Standard High-Volume Markets
                active = [m for m in markets if m.get('active') is True and float(m.get('volume24hr', 0)) >= min_volume]
                
                # 2. High-Frequency 'Up or Down' Markets (force-include)
                hf_keywords = getattr(config, 'HF_KEYWORDS', [])
                hf = [m for m in markets if any(k in m.get('question','') for k in hf_keywords)]
                
                # Merge and unique (using market ID)
                seen_ids = set()
                combined = []
                for m in (hf[:config.HF_LIMIT] + active):
                    if m['id'] not in seen_ids:
                        combined.append(m)
                        seen_ids.add(m['id'])
                
                return combined[:limit]
            except: pass
        return []

    def get_orderbook(self, token_id):
        """Fetch orderbook for a specific token ID from CLOB REST API or WebSocket."""
        # Use WS cache if data is fresh AND connection is alive
        ws_is_alive = poly_ws.ws and poly_ws.ws.sock and poly_ws.ws.sock.connected
        max_age = getattr(config, 'WS_MAX_AGE_SEC', 10)
        
        if config.WS_ENABLED and ws_is_alive and token_id in poly_ws.orderbooks:
            if poly_ws.is_fresh(token_id, max_age_sec=max_age):
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
            
            # Fetch orderbooks (Try Cache first, no threads needed for memory access)
            obs = {}
            for tid in tids:
                ob = self.get_orderbook(tid)
                if ob: obs[tid] = ob
            
            if not obs or len(obs) < len(tids): return None
            
            # Normalize to yes/no for scanners
            final_obs = {'tokens': obs}
            if len(tids) == 2:
                # Assuming first is YES, second is NO (standard for Polymarket binary)
                final_obs['yes'] = obs.get(tids[0])
                final_obs['no'] = obs.get(tids[1])
            
            return final_obs
        except: return None
