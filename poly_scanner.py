import time
import argparse
from datetime import datetime
from poly_client import PolyClient

import config

def parse_p(p_str):
    """Convert Polymarket cents (ints/strings) to dollars."""
    try: return float(p_str) / 100.0
    except: return None

def get_vwap_price(order_list, target_usd):
    """Calculate the average price to fill target_usd by depth."""
    if not order_list: return None
    
    total_spent = 0
    total_qty = 0
    
    # Sort by price (low to high)
    sorted_orders = sorted(order_list, key=lambda x: float(x['price']))
    
    for order in sorted_orders:
        price = parse_p(order['price'])
        size = float(order.get('size', 0))
        
        # Max USD we can spend at this level
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

def check_internal_arbitrage(market, ob):
    """Check for arbitrage opportunities using VWAP depth and Fees."""
    if not ob: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    yes_list = ob.get('yes', [])
    no_list = ob.get('no', [])
    outcomes = ob.get('outcomes', [])

    fee_multiplier = 1 + (config.FEE_PCT / 100)

    # Scenario 1: Binary
    if (yes_list or no_list) and not outcomes:
        try:
            y_price = get_vwap_price(yes_list, config.TARGET_TRADE_SIZE_USD / 2)
            n_price = get_vwap_price(no_list, config.TARGET_TRADE_SIZE_USD / 2)
            
            if y_price and n_price:
                total_cost = (y_price + n_price) * fee_multiplier
                if total_cost < 1 - (config.MIN_PROFIT_PCT / 100):
                    profit = (1 - total_cost) * 100
                    print_alert("BINARY (NET)", question, total_cost, profit, slug)
        except: pass
            
    # Scenario 2: Multi-outcome
    elif outcomes:
        try:
            target_per_outcome = config.TARGET_TRADE_SIZE_USD / len(outcomes)
            total_sum = 0
            details = []
            
            for outcome in outcomes:
                price = get_vwap_price(outcome.get('asks', []), target_per_outcome)
                if price:
                    total_sum += price
                    details.append(f"{outcome.get('name')}: {price:.3f}")
                else: return
            
            total_cost = total_sum * fee_multiplier
            if total_cost < 1 - (config.MIN_PROFIT_PCT / 100):
                profit = (1 - total_cost) * 100
                print_alert("MULTI (NET)", question, total_cost, profit, slug, details)
        except: pass

def print_alert(type_name, q, total, profit, slug, details=None):
    icon = "🔥"
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] {icon} {type_name} ARBITRAGE FOUND!\n"
    alert_text += f"Market: {q}\n"
    if details: alert_text += f"Details: {', '.join(details)}\n"
    alert_text += f"Total Cost: ${total:.3f} | Net Profit: {profit:.2f}%\n"
    alert_text += f"Link: https://polymarket.com/event/{slug}\n"
    alert_text += "-" * 60 + "\n"
    
    print(alert_text)
    
    try:
        with open('opportunities.log', 'a', encoding='utf-8') as f:
            f.write(alert_text)
    except: pass

# Global Instance
poly = PolyClient()

def main():
    parser = argparse.ArgumentParser(description="Pure Polymarket Arbitrage Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print("Polymarket Internal Arbitrage Scanner (Professional Mode)")
    print(f"Settings: Min Net Profit {config.MIN_PROFIT_PCT}%, Trade Size ${config.TARGET_TRADE_SIZE_USD}\n")
    
    while True:
        try:
            p_active = poly.fetch_active_markets(config.MIN_VOLUME_24H, config.MAX_P_MARKETS)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring {len(p_active)} Polymarket events...")
            
            for market in p_active:
                ob = poly.get_orderbook(market['id'])
                if ob:
                    check_internal_arbitrage(market, ob)
            
            if args.once: break
            time.sleep(config.POLL_INTERVAL_POLY)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()
