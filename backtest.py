import time
import json
import argparse
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient
import config

# Use the same logic as the scanners for parity
from poly_scanner import get_vwap_price as get_poly_vwap
from cross_scanner import get_vwap_price as get_k_vwap, find_kalshi_match_semantic

ARCHIVE_FILE = "market_archive.jsonl"

class BacktestEngine:
    def __init__(self):
        self.poly = PolyClient()
        self.kalshi = KalshiClient()

    def collect_snapshot(self):
        """Fetch and return a complete snapshot of all active markets and their orderbooks."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecting snapshot...")
        p_active = self.poly.fetch_active_markets(config.MIN_VOLUME_24H, config.MAX_P_MARKETS)
        k_active = self.kalshi.fetch_active_markets(config.MAX_K_MARKETS)
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "poly_markets": [],
            "kalshi_markets": k_active
        }
        
        for p_m in p_active:
            ob = self.poly.get_orderbook(p_m['id'])
            if ob:
                snapshot["poly_markets"].append({
                    "market": p_m,
                    "orderbook": ob
                })
        
        return snapshot

    def run_collector(self, interval_sec=300):
        """Continuously collect data and append to jsonl file."""
        print(f"Data Collector started. Saving to {ARCHIVE_FILE}. Interval: {interval_sec}s")
        while True:
            try:
                snap = self.collect_snapshot()
                with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(snap) + "\n")
                time.sleep(interval_sec)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Collector Error: {e}")
                time.sleep(60)

    def analyze_archive(self, file_path):
        """Replay strategy against archived data."""
        print(f"Analyzing {file_path}...")
        total_opportunities = 0
        total_potential_profit = 0
        snapshots_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    snap = json.loads(line)
                    snapshots_count += 1
                    
                    p_markets_data = snap.get('poly_markets', [])
                    k_active = snap.get('kalshi_markets', [])
                    
                    # 1. Internal Poly Arbs
                    for data in p_markets_data:
                        m = data['market']
                        ob = data['orderbook']
                        
                        # Use internal poly_scanner logic (we'd need to refactor scanners to export pure logic)
                        # For now, a simplified check:
                        res = self._check_internal_sim(m, ob)
                        if res:
                            total_opportunities += 1
                            total_potential_profit += res['profit']

                    # 2. Cross-platform
                    # In a real replay, we'd need to cache embeddings for each snapshot
                    # This is just a structural example of the replay flow
        except FileNotFoundError:
            print("Archive file not found.")
            return

        print("\n--- Backtest Results ---")
        print(f"Snapshots Processed: {snapshots_count}")
        print(f"Total Opps Found: {total_opportunities}")
        if total_opportunities > 0:
            print(f"Avg Profit per Opp: {total_potential_profit/total_opportunities:.2f}%")

    def _check_internal_sim(self, market, ob):
        # Simplified simulation logic for the replay
        fee_multiplier = 1 + (config.FEE_PCT / 100)
        y_price = get_poly_vwap(ob.get('yes', []), config.TARGET_TRADE_SIZE_USD / 2)
        n_price = get_poly_vwap(ob.get('no', []), config.TARGET_TRADE_SIZE_USD / 2)
        
        if y_price and n_price:
            total_cost = (y_price + n_price) * fee_multiplier
            if total_cost < 1 - (config.MIN_PROFIT_PCT / 100):
                return {"profit": (1 - total_cost) * 100}
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtesting & Data Collection Suite")
    parser.add_argument("--collect", action="store_true", help="Start collecting live data")
    parser.add_argument("--analyze", type=str, help="Analyze a specific archive file")
    parser.add_argument("--interval", type=int, default=300, help="Collection interval in seconds")
    
    args = parser.parse_args()
    engine = BacktestEngine()
    
    if args.collect:
        engine.run_collector(args.interval)
    elif args.analyze:
        engine.analyze_archive(args.analyze)
    else:
        parser.print_help()
