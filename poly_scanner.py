import time
import argparse
from datetime import datetime
from poly_client import PolyClient
import config
from risk_manager import risk_manager

# Global Instance
poly = PolyClient()

def parse_p(p_str):
    """Convert Polymarket cents (ints/strings) to dollars."""
    try: return float(p_str) / 100.0
    except: return None

def calculate_kelly_size(profit_pct):
    """Calculate trade size based on Kelly Criterion (Conservative)."""
    if profit_pct <= 0: return config.TARGET_TRADE_SIZE_USD
    
    # Simple version: Size scaled by edge
    # Kelly Fraction (0.2) * Edge * Bankroll * Multiplier
    # e.g. 0.2 * 0.02 * 10000 * 10 = 400 USD
    size = config.BANKROLL_USD * (profit_pct / 100) * config.KELLY_FRACTION * 10
    
    # Clamp between target floor and max exposure
    return max(config.TARGET_TRADE_SIZE_USD, min(size, config.MAX_EXPOSURE_PER_MARKET_USD))

def get_vwap_price(order_list, target_usd):
    """Calculate the average price to fill target_usd by depth."""
    if not order_list: return None
    
    total_spent = 0
    total_qty = 0
    sorted_orders = sorted(order_list, key=lambda x: float(x['price']))
    
    for order in sorted_orders:
        price = parse_p(order['price'])
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

def get_dynamic_threshold(market_volume):
    """Adjust minimum profit based on market volume (proxy for volatility)."""
    threshold = config.MIN_PROFIT_PCT
    if not config.VOLATILITY_ADJUSTMENT_ENABLED:
        return threshold
    
    # If volume is low (e.g. < 50k), add a buffer for safety
    if market_volume < 50000:
        threshold += config.HIGH_VOL_PROFIT_BUFFER
    return threshold

def check_internal_arbitrage(market, ob):
    """Check for arbitrage opportunities using VWAP depth and dynamic thresholds."""
    if not ob: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    volume = float(market.get('volume24hr', 0))
    
    # Statistical Adjustment
    min_profit = get_dynamic_threshold(volume)
    fee_multiplier = 1 + (config.FEE_PCT / 100)

    # Scenario 1: Binary
    if (ob.get('yes') or ob.get('no')) and not ob.get('outcomes'):
        try:
            y_price = get_vwap_price(ob.get('yes', []), config.TARGET_TRADE_SIZE_USD / 2)
            n_price = get_vwap_price(ob.get('no', []), config.TARGET_TRADE_SIZE_USD / 2)
            
            if y_price and n_price:
                total_cost = (y_price + n_price) * fee_multiplier
                if total_cost < 1 - (min_profit / 100):
                    profit = (1 - total_cost) * 100
                    rec_size = calculate_kelly_size(profit)
                    
                    # Risk Check
                    can_add, reason = risk_manager.can_add_position(slug, slug, rec_size)
                    risk_msg = "" if can_add else f" [RISK WARNING: {reason}]"
                    
                    print_alert("BINARY (NET)", question, total_cost, profit, slug, volume=volume, size=rec_size, risk_msg=risk_msg)
        except: pass
            
    # Scenario 2: Multi-outcome
    elif ob.get('outcomes'):
        try:
            outcomes = ob['outcomes']
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
            if total_cost < 1 - (min_profit / 100):
                profit = (1 - total_cost) * 100
                rec_size = calculate_kelly_size(profit)
                print_alert("MULTI (NET)", question, total_cost, profit, slug, details, volume=volume, size=rec_size)
        except: pass

def print_alert(type_name, q, total, profit, slug, details=None, volume=0, size=0, risk_msg=""):
    icon = "🔥"
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] {icon} {type_name} ARBITRAGE FOUND!{risk_msg}\n"
    alert_text += f"Market: {q}\n"
    alert_text += f"Market Volume: ${volume:,.0f}\n"
    if details: alert_text += f"Details: {', '.join(details)}\n"
    alert_text += f"Total Cost: ${total:.3f} | Net Profit: {profit:.2f}%\n"
    alert_text += f"Recommended Size: ${size:,.0f} (Kelly)\n"
    alert_text += f"Link: https://polymarket.com/event/{slug}\n"
    alert_text += "-" * 60 + "\n"
    
    print(alert_text)
    
    try:
        with open('opportunities.log', 'a', encoding='utf-8') as f:
            f.write(alert_text)
    except: pass

def main():
    parser = argparse.ArgumentParser(description="Professional Polymarket Arbitrage Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print("Polymarket Internal Arbitrage Scanner (Professional Suite)")
    print(f"Base Profit: {config.MIN_PROFIT_PCT}% | Fee Adjustment: {config.FEE_PCT}%\n")
    
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
