import json
import time
import concurrent.futures
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient
import config

# Use logic from cross_scanner for VWAP and matching
from cross_scanner import get_vwap_price as calc_vwap, find_kalshi_match_semantic
from poly_scanner import calculate_kelly_size, get_dynamic_threshold

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

        print(f"  - Fetching {len(all_token_tasks)} orderbooks for {len(p_active)} Poly markets...")
        
        token_to_ob = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_tid = {executor.submit(self.poly.get_orderbook, tid): tid for _, tid in all_token_tasks}
            
            count = 0
            for future in concurrent.futures.as_completed(future_to_tid):
                count += 1
                tid = future_to_tid[future]
                try:
                    ob = future.result()
                    if ob: token_to_ob[tid] = ob
                except: pass
                
                if count % 20 == 0 or count == len(all_token_tasks):
                    print(f"    Progress: {count}/{len(all_token_tasks)}...", end='\r', flush=True)

        # Re-assemble into snapshots
        for m in p_active:
            token_ids = json.loads(m.get('clobTokenIds', '[]'))
            outcomes = m.get('outcomes', [])
            
            market_obs = {}
            # Map common names to YES/NO for binary logic
            if len(token_ids) == 2:
                market_obs['yes'] = token_to_ob.get(token_ids[0])
                market_obs['no'] = token_to_ob.get(token_ids[1])
            
            # Also store with token_ids as keys for multi-outcome
            market_obs['tokens'] = {tid: token_to_ob.get(tid) for tid in token_ids}
            
            snapshot["poly_markets"].append({
                "market": m,
                "orderbook": market_obs
            })

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

    def analyze_archive(self, file_path):
        """Replay strategy against archived data with basic metrics."""
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
                    current_snap_profit = 0
                    
                    for data in p_markets_data:
                        m = data['market']
                        ob = data['orderbook']
                        res = self._check_internal_sim(m, ob)
                        if res:
                            total_opportunities += 1
                            current_snap_profit += res['profit']

                    total_potential_profit += current_snap_profit

        except FileNotFoundError:
            print("Archive file not found.")
            return

        print("\n" + "="*40)
        print("   BACKTEST REPORT   ")
        print("="*40)
        print(f"Snapshots:      {snapshots_count}")
        print(f"Opportunities:  {total_opportunities}")
        print(f"Total Return:   {total_potential_profit:.2f}%")
        print("="*40)

    def _check_internal_sim(self, m, ob):
        # Simulated check using YES/NO books
        try:
            y_book = ob.get('yes', {}).get('asks', [])
            n_book = ob.get('no', {}).get('asks', [])
            
            p1 = calc_vwap(y_book, config.TARGET_TRADE_SIZE_USD / 2)
            p2 = calc_vwap(n_book, config.TARGET_TRADE_SIZE_USD / 2)
            
            if not p1 or not p2: return None
            
            total = p1 + p2
            threshold = get_dynamic_threshold(float(m.get('volume24hr', 0)))
            
            if total < (1.0 - (threshold / 100)):
                profit = (1.0 / total - 1) * 100
                return {"profit": profit}
        except: pass
        return None

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
