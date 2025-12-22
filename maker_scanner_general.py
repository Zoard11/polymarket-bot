import time
import argparse
import concurrent.futures
from datetime import datetime
from poly_client import PolyClient
import config

# Global Instance
poly = PolyClient()

# General Maker Settings (Looser/Slower)
MAKER_MIN_SPREAD_PROFIT = 2.0  # 2% spread
MAKER_POLL_INTERVAL = 15.0     # Slower poll for 200 markets to avoid rate limits

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
    
    if y_bid > 0 and n_bid > 0:
        current_implied_cost = y_bid + n_bid
        
        # Profit = 1.00 - Cost
        potential_profit_pct = (1.0 - current_implied_cost) * 100
        
        if potential_profit_pct >= MAKER_MIN_SPREAD_PROFIT:
            print_maker_alert(question, current_implied_cost, potential_profit_pct, y_bid, n_bid, slug)

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
    args = parser.parse_args()

    print("🐢 General Maker Strategy Scanner (Wide Net - 200 Markets) Started...")
    
    while True:
        try:
            # Fetch ALL active markets
            markets = poly.fetch_active_markets(limit=config.MAX_P_MARKETS)
            
            # No KW filter -> Scan everything
            targets = markets

            # Parallel Fetch
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_market = {executor.submit(poly.get_market_orderbooks, m): m for m in targets}
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
