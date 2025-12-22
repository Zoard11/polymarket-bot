import time
import sys
import argparse
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient

# Configuration
MIN_PROFIT_PCT = 1.0          
MIN_VOLUME_24H = 10000        
MIN_LIQUIDITY_USD = 100       
POLL_INTERVAL = 15            
MAX_P_MARKETS = 100           
MAX_K_MARKETS = 1000          

# Global Instances
poly = PolyClient()
kalshi = KalshiClient()

def parse_p(p_str):
    """Convert Polymarket cents (ints/strings) to dollars."""
    try: return float(p_str) / 100.0
    except: return None

def get_word_set(text):
    if not text: return set()
    return set(text.lower().replace('?', '').replace('.', '').split())

def find_kalshi_match(poly_question, kalshi_markets):
    poly_words = get_word_set(poly_question)
    if len(poly_words) < 3: return None
    
    best_match = None
    max_similarity = 0.4 
    
    for km in kalshi_markets:
        km_text = (km.get('title', '') + " " + km.get('subtitle', '')).strip()
        km_words = get_word_set(km_text)
        
        intersection = poly_words.intersection(km_words)
        union = poly_words.union(km_words)
        similarity = len(intersection) / len(union) if union else 0
        
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = km
            
    return best_match

def check_arbitrage(market, ob):
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
            
    # Scenario 2: Multi-outcome
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

def check_cross_platform_arb(poly_market, poly_ob, kalshi_market):
    """Check for arbitrage between Polymarket and Kalshi."""
    # Note: Cross-matching is experimental and requires precise outcome mapping.
    pass

def print_alert(type_name, q, total, profit, slug, details=None):
    icon = "🔥" if type_name == "BINARY" else "🚨"
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {icon} {type_name} ARBITRAGE FOUND!")
    print(f"Market: {q}")
    if details: print(f"Details: {', '.join(details)}")
    print(f"Total Cost: ${total:.3f} | Profit: {profit:.2f}%")
    print(f"Link: https://polymarket.com/event/{slug}")
    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Polymarket & Kalshi Arbitrage Scanner")
    parser.add_argument("--once", action="store_true", help="Run the scan once and exit")
    args = parser.parse_args()

    print("Polymarket & Kalshi Arbitrage Scanner (Refactored)")
    print(f"Settings: Min Profit {MIN_PROFIT_PCT}%, Min Liquidity ${MIN_LIQUIDITY_USD}\n")
    
    while True:
        try:
            p_active = poly.fetch_active_markets(MIN_VOLUME_24H, MAX_P_MARKETS)
            k_active = kalshi.fetch_active_markets(MAX_K_MARKETS)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(p_active)} Poly vs {len(k_active)} Kalshi markets...")
            
            for market in p_active:
                ob = poly.get_orderbook(market['id'])
                if not ob: continue
                
                check_arbitrage(market, ob)
            
            if args.once:
                print("\nSingle scan completed (--once). Exiting.")
                break
                
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
