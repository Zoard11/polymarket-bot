import time
import argparse
from datetime import datetime
from poly_client import PolyClient

# Configuration
MIN_PROFIT_PCT = 1.0          
MIN_VOLUME_24H = 10000        
MIN_LIQUIDITY_USD = 100       
POLL_INTERVAL = 15 # Faster polling for Poly-only
MAX_P_MARKETS = 200           

# Global Instance
poly = PolyClient()

def parse_p(p_str):
    """Convert Polymarket cents (ints/strings) to dollars."""
    try: return float(p_str) / 100.0
    except: return None

def check_internal_arbitrage(market, ob):
    """Check for arbitrage opportunities on a single market (YES+NO < 1)."""
    if not ob: return
    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    yes_list = ob.get('yes', [])
    no_list = ob.get('no', [])
    outcomes = ob.get('outcomes', [])

    # Scenario 1: Binary
    if (yes_list or no_list) and not outcomes:
        try:
            y_best = min(yes_list, key=lambda x: float(x['price'])) if yes_list else None
            n_best = min(no_list, key=lambda x: float(x['price'])) if no_list else None
            
            if y_best and n_best:
                y_ask = parse_p(y_best['price'])
                n_ask = parse_p(n_best['price'])
                
                if (y_ask * float(y_best.get('size', 0)) >= MIN_LIQUIDITY_USD and 
                    n_ask * float(n_best.get('size', 0)) >= MIN_LIQUIDITY_USD):
                    
                    total = y_ask + n_ask
                    if total < 1 - (MIN_PROFIT_PCT / 100):
                        print_alert("BINARY", question, total, (1-total)*100, slug)
        except: pass
            
    # Scenario 2: Multi-outcome (Categorical)
    elif outcomes:
        try:
            total_sum = 0
            details = []
            min_liq = float('inf')
            
            for outcome in outcomes:
                asks = outcome.get('asks', [])
                if asks:
                    best = min(asks, key=lambda x: float(x['price']))
                    price = parse_p(best['price'])
                    total_sum += price
                    min_liq = min(min_liq, price * float(best.get('size', 0)))
                    details.append(f"{outcome.get('name')}: {price:.3f}")
                else: return
            
            if min_liq >= MIN_LIQUIDITY_USD and total_sum < 1 - (MIN_PROFIT_PCT / 100):
                print_alert("MULTI", question, total_sum, (1-total_sum)*100, slug, details)
        except: pass

def print_alert(type_name, q, total, profit, slug, details=None):
    icon = "🔥"
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] {icon} {type_name} ARBITRAGE FOUND!\n"
    alert_text += f"Market: {q}\n"
    if details: alert_text += f"Details: {', '.join(details)}\n"
    alert_text += f"Total Cost: ${total:.3f} | Profit: {profit:.2f}%\n"
    alert_text += f"Link: https://polymarket.com/event/{slug}\n"
    alert_text += "-" * 60 + "\n"
    
    print(alert_text)
    
    # Log to persistent opportunities file
    try:
        with open('opportunities.log', 'a', encoding='utf-8') as f:
            f.write(alert_text)
    except: pass

def main():
    parser = argparse.ArgumentParser(description="Pure Polymarket Arbitrage Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print("Polymarket Internal Arbitrage Scanner (Pure Mode)")
    print(f"Settings: Profit >{MIN_PROFIT_PCT}%, Vol >${MIN_VOLUME_24H}\n")
    
    while True:
        try:
            p_active = poly.fetch_active_markets(MIN_VOLUME_24H, MAX_P_MARKETS)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(p_active)} Polymarket events...")
            
            for market in p_active:
                ob = poly.get_orderbook(market['id'])
                if ob:
                    check_internal_arbitrage(market, ob)
            
            if args.once: break
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()
