import time
import json
import argparse
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient
import config

# Use the same logic as the scanners for parity
from poly_scanner import get_vwap_price as get_poly_vwap, calculate_kelly_size, get_dynamic_threshold
from cross_scanner import get_vwap_price as get_k_vwap, find_kalshi_match_semantic
from risk_manager import RiskManager

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
        """Replay strategy against archived data with advanced metrics."""
        print(f"Analyzing {file_path}...")
        results = []
        equity_curve = [0]
        timestamps = []
        
        total_opportunities = 0
        total_potential_profit = 0
        snapshots_count = 0
        
        # Local risk manager for the simulation
        sim_risk = RiskManager()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    snap = json.loads(line)
                    snapshots_count += 1
                    
                    p_markets_data = snap.get('poly_markets', [])
                    k_active = snap.get('kalshi_markets', [])
                    current_snap_profit = 0
                    
                    # 1. Internal Poly Arbs
                    for data in p_markets_data:
                        m = data['market']
                        ob = data['orderbook']
                        
                        # Use internal poly_scanner logic (we'd need to refactor scanners to export pure logic)
                        # For now, a simplified check:
                        res = self._check_internal_sim(m, ob, sim_risk)
                        if res:
                            total_opportunities += 1
                            current_snap_profit += res['profit_usd']
                            # Count profit in % for the general return stat too
                            total_potential_profit += res['profit_pct'] 

                    # 2. Cross-platform
                    k_embeddings = None
                    if k_active:
                        # Re-calculate embeddings for this snapshot
                        try:
                            from sentence_transformers import SentenceTransformer, util
                            model = SentenceTransformer('all-MiniLM-L6-v2')
                            k_texts = [(km.get('title', '') + " " + km.get('subtitle', '')).lower() for km in k_active]
                            k_embeddings = model.encode(k_texts, convert_to_tensor=True)
                        except: pass

                    for data in p_markets_data:
                        m = data['market']
                        ob = data['orderbook']
                        
                        # Cross match
                        k_match = find_kalshi_match_semantic(m, k_active, k_embeddings)
                        if k_match:
                            res = self._check_cross_sim(m, ob, k_match, sim_risk)
                            if res:
                                total_opportunities += 1
                                current_snap_profit += res['profit_usd']
                                total_potential_profit += res['profit_pct']

                    total_potential_profit += current_snap_profit
                    equity_curve.append(equity_curve[-1] + current_snap_profit)
                    timestamps.append(snap.get('timestamp'))

        except FileNotFoundError:
            print("Archive file not found.")
            return

        # --- Statistics Calculation ---
        import numpy as np
        returns = np.diff(equity_curve)
        
        sharp_ratio = 0
        if len(returns) > 1 and np.std(returns) > 0:
            sharp_ratio = np.mean(returns) / np.std(returns) * np.sqrt(365 * 24 * (3600 / 300)) # Annualized from 5m bins
            
        # Max Drawdown
        max_drawdown = 0
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak: peak = val
            drawdown = peak - val
            if drawdown > max_drawdown: max_drawdown = drawdown

        print("\n" + "="*40)
        print("   PROFESSIONAL BACKTEST REPORT   ")
        print("="*40)
        print(f"Snapshots Processed: {snapshots_count}")
        print(f"Total Opps Found:    {total_opportunities}")
        print(f"Total Theoretical Profit: ${total_potential_profit:,.2f} USD")
        print(f"Avg Profit/Trade:    {total_potential_profit/max(1, total_opportunities):.2f}%")
        print("-" * 40)
        print(f"Sharpe Ratio:        {sharp_ratio:.2f}")
        print(f"Max Drawdown:        {max_drawdown:.2f}%")
        print(f"Expectancy:          {total_potential_profit/max(1, snapshots_count):.4f}% per interval")
        print("="*40)

    def _check_internal_sim(self, market, ob, risk_mgr):
        volume = float(market.get('volume24hr', 0))
        min_profit = get_dynamic_threshold(volume)
        fee_multiplier = 1 + (config.FEE_PCT / 100)
        
        y_price = get_poly_vwap(ob.get('yes', []), config.TARGET_TRADE_SIZE_USD / 2)
        n_price = get_poly_vwap(ob.get('no', []), config.TARGET_TRADE_SIZE_USD / 2)
        
        if y_price and n_price:
            total_cost = (y_price + n_price) * fee_multiplier
            if total_cost < 1 - (min_profit / 100):
                profit_pct = (1 - total_cost) * 100
                rec_size = calculate_kelly_size(profit_pct)
                
                # Simulation risk check
                can_add, _ = risk_mgr.can_add_position(market['slug'], market['slug'], rec_size)
                if can_add:
                    risk_mgr.record_trade(market['slug'], market['slug'], rec_size)
                    return {"profit_usd": (profit_pct/100) * rec_size, "profit_pct": profit_pct}
        return None

    def _check_cross_sim(self, poly_market, poly_ob, kalshi_market, risk_mgr):
        fee_multiplier = 1 + (config.FEE_PCT / 100)
        volume = float(poly_market.get('volume24hr', 0))
        min_profit = get_dynamic_threshold(volume)
        target_leg = config.TARGET_TRADE_SIZE_USD / 2 # Fallback for VWAP
        
        p_yes_vwap = get_poly_vwap(poly_ob.get('yes', []), target_leg)
        p_no_vwap = get_poly_vwap(poly_ob.get('no', []), target_leg)
        
        # Simplified assumption for backtest: Kalshi depth matches Poly approx or uses best quotes
        # In a real replay we'd need Kalshi depth too.
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
