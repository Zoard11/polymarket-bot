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

def get_liquidity_depth(order_list, best_p):
    """Calculate total USD depth at the best bid price."""
    if not order_list or not best_p: return 0.0
    # Sum up USD size of all orders at the best price
    depth = sum(float(o.get('size', 0)) * best_p for o in order_list if parse_p(o.get('price')) == best_p)
    return depth

def check_maker_opportunity(market, obs):
    if not obs: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    # Get Bids
    y_orders = obs.get('yes', {}).get('bids', [])
    n_orders = obs.get('no', {}).get('bids', [])
    
    y_bid = get_best_bid(y_orders)
    n_bid = get_best_bid(n_orders)
    
    # Dead Market Check
    if not config.MAKER_ALLOW_DEAD_MARKETS:
        if y_bid == 0 or n_bid == 0: return

    # LIQUIDITY DEPTH CHECK (New! Based on feedback)
    y_depth = get_liquidity_depth(y_orders, y_bid)
    n_depth = get_liquidity_depth(n_orders, n_bid)
    total_liquidity = y_depth + n_depth
    
    min_liq = getattr(config, 'MIN_LIQUIDITY_USD', 10.0)
    if total_liquidity < min_liq:
        # Silently skip thin markets to avoid spamming console
        return

    current_implied_cost = y_bid + n_bid
    
    # Profit = 1.00 - Cost
    potential_profit_pct = (1.0 - current_implied_cost) * 100
    
    if potential_profit_pct >= config.MAKER_MIN_PROFIT_PCT:
        print_maker_alert(question, current_implied_cost, potential_profit_pct, y_bid, n_bid, slug, total_liquidity)
        
        # TRIGGER EXECUTION
        try:
            # Use size from arguments or config
            size = getattr(config, 'CURRENT_RUN_SIZE', config.MAKER_TRADE_SIZE_USD)
            executor.place_maker_orders(market, y_bid, n_bid, size_usd=size)
        except Exception as e:
            print(f"❌ EXECUTION CRASHED: {e}")

def print_maker_alert(q, cost, profit, y_bid, n_bid, slug, liquidity):
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] [MAKER-GEN] 🐢 SLOW SPREAD FOUND!\n"
    alert_text += f"Market: {q}\n"
    alert_text += f"Current Bids: YES {y_bid:.2f} + NO {n_bid:.2f} = {cost:.2f}\n"
    alert_text += f"Spread Profit: {profit:.2f}% | Depth: ${liquidity:.2f}\n"
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

    print("🚀 Speed-Optimized Maker Strategy Scanner (WebSocket-First) Started...")
    
    cached_markets = []
    last_hedge_check = 0
    HEDGE_CHECK_INTERVAL = getattr(config, 'HEDGE_CHECK_INTERVAL_SEC', 30)

    while True:
        try:
            now = time.time()
            
            # 0. PERIODIC HEDGE CHASER: Check status of pending hedges
            if config.LIVE_TRADING and (now - last_hedge_check > HEDGE_CHECK_INTERVAL):
                executor.check_and_chase_hedges()
                last_hedge_check = now

            # 1. Periodically fetch/refresh market list (REST - Slow handled safely)
            if not cached_markets or (now - last_market_refresh > MARKET_REFRESH_SEC):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Refreshing market list from Gamma API...")
                cached_markets = poly.fetch_active_markets(limit=config.MAX_P_MARKETS)
                last_market_refresh = now
                
                # Subscribe to WebSocket for all market tokens
                if config.WS_ENABLED and cached_markets:
                    token_ids = []
                    for m in cached_markets:
                        tids = m.get('clobTokenIds')
                        if isinstance(tids, str):
                            import json
                            tids = json.loads(tids)
                        if tids: token_ids.extend(tids)
                    if token_ids:
                        poly_ws.subscribe(list(set(token_ids)))
                        print(f"🌐 Subscribed to {len(token_ids)} tokens on WebSocket.")

            # 2. FAST PATH: Check opportunities
            # With 3 CPUs, a serial loop for 200 dict lookups is actually FASTER 
            # than the overhead of a ThreadPool.
            for market in cached_markets:
                obs = poly.get_market_orderbooks(market)
                if obs:
                    check_maker_opportunity(market, obs)
            
            if args.once: break
            
            # Use small interval for WS cache check
            interval = getattr(config, 'POLL_INTERVAL_WS', 0.5)
            time.sleep(interval)

        except KeyboardInterrupt: break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Loop error: {e}")
            time.sleep(15) # Safety sleep on crash

if __name__ == "__main__":
    main()
