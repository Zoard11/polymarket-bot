import time
import argparse
import concurrent.futures
from datetime import datetime
from poly_client import PolyClient
import config

# Global Instance
poly = PolyClient()

# Maker Settings
MAKER_MIN_SPREAD_PROFIT = 2.0  # We want at least 2% profit margin on our limit orders
MAKER_POLL_INTERVAL = 1.0      # Checking speed

def parse_p(p_str):
    try:
        val = float(p_str)
        if val > 1.0: return val / 100.0
        return val
    except: return None

def get_best_bid(order_list):
    """Get the highest price someone is currently willing to pay (Best Bid)."""
    if not order_list: return 0.0
    # Orders are usually sorted, but let's be safe. Best bid is MAX price.
    prices = [parse_p(o.get('price')) for o in order_list if parse_p(o.get('price')) is not None]
    if not prices: return 0.0
    return max(prices)

def check_maker_opportunity(market, obs):
    """
    Check if the current Bids allow for a profitable Maker strategy.
    Strategy: Place bids on YES and NO such that cost < 1.0.
    We look for markets where the existing Best Bids sum to < 1.0 - margin.
    This implies we can join the Best Bid (or improve it slightly) and still be profitable.
    """
    if not obs: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    # Get Best Bids (The "Traps" currently set)
    y_bid = get_best_bid(obs.get('yes', {}).get('bids', []))
    n_bid = get_best_bid(obs.get('no', {}).get('bids', []))
    
    if y_bid > 0 and n_bid > 0:
        current_implied_cost = y_bid + n_bid
        
        # If I matched these bids, would I make money?
        # Cost = Bid_YES + Bid_NO
        # Payout = 1.00
        # Profit = 1.00 - Cost
        
        potential_profit_pct = (1.0 - current_implied_cost) * 100
        
        if potential_profit_pct >= MAKER_MIN_SPREAD_PROFIT:
            print_maker_alert(question, current_implied_cost, potential_profit_pct, y_bid, n_bid, slug)

def print_maker_alert(q, cost, profit, y_bid, n_bid, slug):
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] [MAKER] ☕ SPREAD OPPORTUNITY!\n"
    alert_text += f"Market: {q}\n"
    alert_text += f"Current Bids: YES {y_bid:.2f} + NO {n_bid:.2f} = {cost:.2f}\n"
    alert_text += f"Spread Profit: {profit:.2f}% (If you join/lead these bids)\n"
    alert_text += f"Link: https://polymarket.com/event/{slug}\n"
    alert_text += "-" * 40 + "\n"
    print(alert_text)
    try:
        with open('opportunities.log', 'a', encoding='utf-8') as f:
            f.write(alert_text)
    except: pass

def main():
    parser = argparse.ArgumentParser(description="Maker Strategy / Spread Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print("☕ Maker Strategy Scanner (Coffee Bot Clone) Started...")
    
    while True:
        try:
            # Focus on HF markets for now as requested
            markets = poly.fetch_active_markets(limit=config.HF_LIMIT)
            # Filter specifically for likely Maker targets (HF or High Vol)
            targets = [m for m in markets if any(k in m.get('question','') for k in config.HF_KEYWORDS)]
            
            # If no HF keywords found, fallback to top volume markets to show functionality
            if not targets:
                targets = markets[:20]

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
            print(f"Maker Loop Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
