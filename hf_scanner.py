import time
import argparse
import json
import concurrent.futures
from datetime import datetime
from poly_client import PolyClient
import config
from risk_manager import risk_manager
from ws_client import poly_ws

# Global Instance
poly = PolyClient()

# Specialized settings for 15-min markets
HF_TARGET_TRADE_SIZE = 50       # Smaller size for lower liquidity
HF_MIN_PROFIT_PCT = 0.5         # Thinner margins acceptable for high turn
HF_POLL_INTERVAL = 0.2          # Aggressive checking

def parse_p(p_str):
    """Convert Polymarket price to decimal (0-1)."""
    try:
        val = float(p_str)
        if val > 1.0: return val / 100.0
        return val
    except: return None

def get_vwap_price(order_list, target_usd):
    """Calculate the average price to fill target_usd by depth."""
    if not order_list: return None
    total_spent = 0
    total_qty = 0
    sorted_orders = sorted(order_list, key=lambda x: float(p_str) if (p_str := x.get('price')) else 0)
    for order in sorted_orders:
        price = parse_p(order.get('price'))
        size = float(order.get('size', 0))
        max_usd_level = price * size
        remaining_to_fill = target_usd - total_spent
        if max_usd_level >= remaining_to_fill:
            qty_needed = remaining_to_fill / price
            total_spent += remaining_to_fill
            total_qty += qty_needed
            return total_spent / total_qty
        else:
            total_spent += max_usd_level
            total_qty += size
    return None

def check_hf_arbitrage(market, obs):
    """Check for arbitrage in Up/Down 15m markets."""
    if not obs: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    # HF Fee adjustment (usually lower or zero if maker, but using config default)
    fee_multiplier = 1 + (config.FEE_PCT / 100)
    
    y_price = get_vwap_price(obs.get('yes', {}).get('asks', []), HF_TARGET_TRADE_SIZE / 2)
    n_price = get_vwap_price(obs.get('no', {}).get('asks', []), HF_TARGET_TRADE_SIZE / 2)
    
    if y_price and n_price:
        total_cost = (y_price + n_price) * fee_multiplier
        if total_cost < 1 - (HF_MIN_PROFIT_PCT / 100):
            profit = (1 - total_cost) * 100
            print_hf_alert(question, total_cost, profit, slug)

def print_hf_alert(q, total, profit, slug):
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] [HF] ⚡ 15m ARBITRAGE!\n"
    alert_text += f"Market: {q}\n"
    alert_text += f"Total Cost: ${total:.3f} | Profit: {profit:.2f}%\n"
    alert_text += f"Link: https://polymarket.com/event/{slug}\n"
    alert_text += "-" * 40 + "\n"
    print(alert_text)
    try:
        with open('opportunities.log', 'a', encoding='utf-8') as f:
            f.write(alert_text)
    except: pass

def main():
    parser = argparse.ArgumentParser(description="High-Frequency 15-Minute Market Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print("HF 15-Minute Market Scanner (Active)")
    
    while True:
        try:
            # specifically fetch HF markets
            markets = poly.fetch_active_markets(limit=config.HF_LIMIT)
            hf_targets = [m for m in markets if any(k in m.get('question','') for k in config.HF_KEYWORDS)]
            
            if not hf_targets:
                time.sleep(10)
                continue

            # Parallel OB fetch for these ultra-fast markets
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_market = {executor.submit(poly.get_market_orderbooks, m): m for m in hf_targets}
                for future in concurrent.futures.as_completed(future_to_market):
                    market = future_to_market[future]
                    obs = future.result()
                    if obs:
                        check_hf_arbitrage(market, obs)
            
            if args.once: break
            time.sleep(HF_POLL_INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"HF Loop Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
