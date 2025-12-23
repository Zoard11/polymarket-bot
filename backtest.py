import json
import time
import concurrent.futures
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient
import config

# Comprehensive Strategy Imports
from cross_scanner import get_vwap_price as calc_vwap
from poly_scanner import calculate_kelly_size, get_dynamic_threshold, check_internal_arbitrage
from maker_scanner import check_maker_opportunity
from hf_scanner import check_hf_arbitrage
from cross_scanner import check_cross_platform_arb

ARCHIVE_FILE = "market_archive.jsonl"

class BacktestEngine:
    """
    Handles data collection and strategy replay for backtesting.
    """
    def __init__(self):
        self.poly = PolyClient()
        self.kalshi = KalshiClient()

    def collect_snapshot(self):
        """Fetch and return a complete snapshot of all active markets and their orderbooks."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecting snapshot (Parallel)...")
        p_active = self.poly.fetch_active_markets(config.MIN_VOLUME_24H, config.MAX_P_MARKETS)
        k_active = self.kalshi.fetch_active_markets(config.MAX_K_MARKETS)
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "poly_markets": [],
            "kalshi_markets": k_active
        }
        
        # We need to collect orderbooks for YES and NO tokens separately
        all_token_tasks = []
        for m in p_active:
            token_ids = json.loads(m.get('clobTokenIds', '[]'))
            for tid in token_ids:
                all_token_tasks.append((m, tid))

        print(f"  - Fetching orderbooks for {len(p_active)} Poly markets using parallel threads...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_market = {executor.submit(self.poly.get_market_orderbooks, m): m for m in p_active}
            
            for future in concurrent.futures.as_completed(future_to_market):
                market = future_to_market[future]
                try:
                    market_obs = future.result()
                    if market_obs:
                        snapshot["poly_markets"].append({
                            "market": market,
                            "orderbook": market_obs
                        })
                except: pass
                
        print(f"\n  - Poly Snapshot Complete: {len(snapshot['poly_markets'])} markets captured.")
        print(f"  - Kalshi: {len(snapshot['kalshi_markets'])} markets")
        return snapshot

    def run_collector(self, interval_sec=300, once=False):
        """Continuously collect data and append to jsonl file."""
        print(f"Data Collector started. Saving to {ARCHIVE_FILE}. Interval: {interval_sec}s")
        
        while True:
            try:
                snap = self.collect_snapshot()
                with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(snap) + "\n")
                    f.flush()
                print(f"  - Snapshot recorded safely to {ARCHIVE_FILE}")
                if once: break
                time.sleep(interval_sec)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Collector Error: {e}")
                time.sleep(60)

    def _check_internal_sim(self, m, ob):
        # 1. Sniper Strategy (Taker): Check Asks
        try:
            y_asks = ob.get('yes', {}).get('asks', [])
            n_asks = ob.get('no', {}).get('asks', [])
            
            p1 = calc_vwap(y_asks, config.TARGET_TRADE_SIZE_USD / 2)
            p2 = calc_vwap(n_asks, config.TARGET_TRADE_SIZE_USD / 2)
            
            if p1 and p2:
                total = p1 + p2
                threshold = get_dynamic_threshold(float(m.get('volume24hr', 0)))
                
                # Check Taker Arb
                if total < (1.0 - (threshold / 100)):
                    profit = (1.0 / total - 1) * 100
                    return {"type": "SNIPER", "profit": profit}
        except: pass

        # 2. Maker Strategy (Coffee Bot): Check Bids
        # If Best Bid YES + Best Bid NO < 0.98, we can join both sides and capture spread
        try:
            y_bids = ob.get('yes', {}).get('bids', [])
            n_bids = ob.get('no', {}).get('bids', [])
            
            # Simple max bid check
            b1 = float(y_bids[0]['price']) if y_bids else 0
            b2 = float(n_bids[0]['price']) if n_bids else 0
            
            if b1 > 0 and b2 > 0:
                cost_to_make = b1 + b2
                # Target at least 1% spread?
                if cost_to_make < 0.99: 
                    spread = (1.0 - cost_to_make) * 100
                    return {"type": "MAKER", "profit": spread}
        except: pass
        
        return None

    def analyze_archive(self, file_path):
        """
        Replay ALL strategies against archived data.
        """
        print(f"Deep Backtest Analysis: {file_path}")
        stats = {
            "POLY_INTERNAL": 0,
            "HF_SCALPING": 0,
            "MAKER_HF": 0,
            "MAKER_GEN": 0,
            "CROSS_PLATFORM": 0,
            "CORRELATED": 0
        }
        
        maker_hits = [] 

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    snap = json.loads(line)
                    p_markets = snap.get('poly_markets', [])
                    k_markets = snap.get('kalshi_markets', [])
                    
                    for row in p_markets:
                        m = row['market']
                        ob = row['orderbook']
                        
                        # 1. POLY INTERNAL
                        if self._sim_poly_internal(m, ob): stats["POLY_INTERNAL"] += 1
                        
                        # 2. HF SCALPING
                        if self._sim_hf(m, ob): stats["HF_SCALPING"] += 1

                        # 3. MAKER (SPLIT)
                        # Uses config.MAKER_MIN_PROFIT_PCT and config.MAKER_ALLOW_DEAD_MARKETS dynamically
                        is_maker = self._sim_maker(m, ob)
                        if is_maker:
                            # Classify as HF or Gen
                            if "Up or Down" in m.get('question', ''):
                                stats["MAKER_HF"] += 1
                            else:
                                stats["MAKER_GEN"] += 1
                                maker_hits.append(m.get('question'))

                        # 4. CROSS PLATFORM
                        if k_markets:
                            p_slug = m.get('slug', '').lower()
                            # Simple substring match
                            for km in k_markets:
                                if km.get('ticker', '').lower() in p_slug:
                                    if self._sim_cross(m, ob, km): 
                                        stats["CROSS_PLATFORM"] += 1
                                    break
                        
        except Exception as e:
            print(f"Analysis failed: {e}")
            return

        print("\n" + "="*50)
        print("   🚀 COMPREHENSIVE BACKTEST RESULTS (7 SCRIPTS)   ")
        print("="*50)
        print(f"1. POLY_INTERNAL    : {stats['POLY_INTERNAL']} opps")
        print(f"2. CROSS_PLATFORM   : {stats['CROSS_PLATFORM']} opps")
        print(f"3. CORRELATED       : {stats['CORRELATED']} opps (Skeleton)")
        print(f"4. HF_SCALPING      : {stats['HF_SCALPING']} opps")
        print(f"5. MAKER_HF         : {stats['MAKER_HF']} opps")
        print(f"6. MAKER_GEN        : {stats['MAKER_GEN']} opps")
        print("-" * 50)
        print("TOP 5 GENERAL MAKER MATCHES:")
        for name in list(set(maker_hits))[:5]:
            print(f" - {name}")
        print("="*50)
    
    def _sim_cross(self, pm, pob, km):
        # Placeholder for cross-platform check using just prices
        # Real logic is in cross_scanner.py
        return False

    # Simulation Wrappers (Adapters)
    def _sim_maker(self, m, ob):
        try:
            # 0. High-Volume Check (New!)
            vol = float(m.get('volume24hr', 0))
            min_vol = getattr(config, 'MIN_VOLUME_24H', 10000)
            if vol < min_vol:
                return False

            y_bids = ob.get('yes', {}).get('bids', [])
            n_bids = ob.get('no', {}).get('bids', [])
            
            y_bid = float(y_bids[0]['price']) if y_bids else 0
            n_bid = float(n_bids[0]['price']) if n_bids else 0
            
            # 1. Check Dead Markets (Low Liquidity)
            if not config.MAKER_ALLOW_DEAD_MARKETS:
                # Must have at least X cents of bids on both sides to be "Alive"
                if y_bid < config.MAKER_MIN_SIDE_PRICE or n_bid < config.MAKER_MIN_SIDE_PRICE: 
                    return False

            # 2. Queue Depth Check (New!)
            max_depth = getattr(config, 'MAKER_MAX_QUEUE_DEPTH_USD', 500)
            y_depth = sum(float(o.get('size', 0)) * y_bid for o in y_bids if float(o.get('price', 0)) == y_bid)
            n_depth = sum(float(o.get('size', 0)) * n_bid for o in n_bids if float(o.get('price', 0)) == n_bid)
            
            if y_depth > max_depth or n_depth > max_depth:
                return False

            # 3. Check Profit Threshold from Config
            cost = y_bid + n_bid
            threshold = 1.0 - (config.MAKER_MIN_PROFIT_PCT / 100.0)
            
            if cost < threshold:
                return True
        except: pass
        return False

    def _sim_poly_internal(self, m, ob):
        try:
            y_book = ob.get('yes', {}).get('asks', [])
            n_book = ob.get('no', {}).get('asks', [])
            p1 = calc_vwap(y_book, 200)
            p2 = calc_vwap(n_book, 200)
            if p1 and p2 and (p1 + p2 < 0.99): return True
        except: pass
        return False
    def _sim_hf(self, m, ob):
        # HF looks for 'Up or Down' keywords and fast arb
        if "Up or Down" not in m.get('question', ''): return False
        return self._sim_poly_internal(m, ob) # HF uses same math, just faster

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Arbitrage Backtesting Engine")
    parser.add_argument("--collect", action="store_true", help="Start data collection mode")
    parser.add_argument("--analyze", type=str, help="Analyze a specific archive file")
    parser.add_argument("--interval", type=int, default=300, help="Collection interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run only one iteration of collection")
    
    args = parser.parse_args()
    engine = BacktestEngine()
    
    if args.collect:
        engine.run_collector(args.interval, once=args.once)
    elif args.analyze:
        engine.analyze_archive(args.analyze)
    else:
        parser.print_help()
