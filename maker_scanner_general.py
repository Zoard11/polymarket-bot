import time
import argparse
import concurrent.futures
from datetime import datetime
from poly_client import PolyClient
import config
from trade_executor import TradeExecutor

# Global Instance
poly = PolyClient()
executor = TradeExecutor(poly)

# General Maker Settings (from config)
MAKER_POLL_INTERVAL = 15.0     # Slower poll for 200 markets

# Initialize WebSocket for real-time orderbook updates
from ws_client import poly_ws
if config.WS_ENABLED:
    poly_ws.start()
    print("🌐 WebSocket client started for real-time orderbook updates...")

def parse_p(p_str):
    try:
        val = float(p_str)
        if val > 1.0: return val / 100.0
        return val
    except: return None

def get_best_bid(order_list):
    """Get the highest price someone is currently willing to pay (Best Bid)."""
    if not order_list: return 0.0
    prices = [parse_p(o.get('price')) for o in order_list if parse_p(o.get('price')) is not None]
    if not prices: return 0.0
    return max(prices)

def check_maker_opportunity(market, obs):
    if not obs: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    # Get Best Bids
    y_bid = get_best_bid(obs.get('yes', {}).get('bids', []))
    n_bid = get_best_bid(obs.get('no', {}).get('bids', []))
    
    # Dead Market Check
    if not config.MAKER_ALLOW_DEAD_MARKETS:
        if y_bid == 0 or n_bid == 0: return

    current_implied_cost = y_bid + n_bid
    
    # Profit = 1.00 - Cost
    potential_profit_pct = (1.0 - current_implied_cost) * 100
    
    if potential_profit_pct >= config.MAKER_MIN_PROFIT_PCT:
        print_maker_alert(question, current_implied_cost, potential_profit_pct, y_bid, n_bid, slug)
        
        # TRIGGER EXECUTION
        try:
            # Use size from arguments or config
            size = getattr(config, 'CURRENT_RUN_SIZE', config.MAKER_TRADE_SIZE_USD)
            executor.place_maker_orders(market, y_bid, n_bid, size_usd=size)
        except Exception as e:
            print(f"❌ EXECUTION CRASHED: {e}")

def print_maker_alert(q, cost, profit, y_bid, n_bid, slug):
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] [MAKER-GEN] 🐢 SLOW SPREAD FOUND!\n"
    alert_text += f"Market: {q}\n"
    alert_text += f"Current Bids: YES {y_bid:.2f} + NO {n_bid:.2f} = {cost:.2f}\n"
    alert_text += f"Spread Profit: {profit:.2f}% (Limit Order Opportunity)\n"
    alert_text += f"Link: https://polymarket.com/event/{slug}\n"
    alert_text += "-" * 40 + "\n"
    print(alert_text)
    try:
        with open('opportunities.log', 'a', encoding='utf-8') as f:
            f.write(alert_text)
    except: pass

def main():
    parser = argparse.ArgumentParser(description="General Maker Strategy Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--size", type=float, help=f"Set custom trade size (default: ${config.MAKER_TRADE_SIZE_USD})")
    args = parser.parse_args()

    if args.size:
        print(f"💰 Using custom trade size: ${args.size}")
        config.CURRENT_RUN_SIZE = args.size

    mode_str = "LIVE 🚀" if config.LIVE_TRADING else "MOCK (Dry Run) 🔎"
    print(f"🛡️  Trading Mode: {mode_str}")

    print("🐢 General Maker Strategy Scanner (Wide Net - 200 Markets) Started...")
    
    while True:
        try:
            # Fetch ALL active markets
            markets = poly.fetch_active_markets(limit=config.MAX_P_MARKETS)
            
            # No KW filter -> Scan everything
            targets = markets

            # Subscribe to WebSocket for real-time updates (reduces REST API calls)
            if config.WS_ENABLED:
                token_ids = []
                for m in targets:
                    tids = m.get('clobTokenIds')
                    if isinstance(tids, str):
                        import json
                        tids = json.loads(tids)
                    if tids:
                        token_ids.extend(tids)
                if token_ids:
                    poly_ws.subscribe(token_ids)

            # Parallel Fetch
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as thread_pool:
                future_to_market = {thread_pool.submit(poly.get_market_orderbooks, m): m for m in targets}
                for future in concurrent.futures.as_completed(future_to_market):
                    market = future_to_market[future]
                    obs = future.result()
                    if obs:
                        check_maker_opportunity(market, obs)
            
            if args.once: break
            time.sleep(MAKER_POLL_INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"General Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
