import requests
import json
import time
from datetime import datetime
from kalshi_client import KalshiClient

# Polymarket Gamma API
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# Configuration
MIN_PROFIT_PCT = 1.0          # Only show opportunities > 1% profit
MIN_VOLUME_24H = 50000        # Only scan markets with > $50k volume (in USD)
POLL_INTERVAL = 15            # Seconds between full scans
MAX_MARKETS = 50              # Max markets to scan per cycle

# Global instances
kalshi = KalshiClient()
markets_cache = {}

def get_word_set(text):
    """Normalize and tokenize text for comparison."""
    if not text: return set()
    return set(text.lower().replace('?', '').replace('.', '').split())

def find_kalshi_match(poly_question, kalshi_markets):
    """Find a corresponding Kalshi market for a Polymarket question."""
    poly_words = get_word_set(poly_question)
    if len(poly_words) < 3: return None
    
    best_match = None
    max_similarity = 0.4 # Threshold for match
    
    for km in kalshi_markets:
        # Kalshi categorical markets have 'title' or 'subtitle'
        km_text = km.get('title', '') + " " + km.get('subtitle', '')
        km_words = get_word_set(km_text)
        
        intersection = poly_words.intersection(km_words)
        union = poly_words.union(km_words)
        similarity = len(intersection) / len(union) if union else 0
        
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = km
            
    return best_match

def check_cross_platform_arb(poly_market, poly_ob, kalshi_market):
    """Check for arbitrage between Polymarket and Kalshi."""
    poly_yes_ask = None
    poly_no_ask = None
    
    # Polymarket Asks
    yes = poly_ob.get('yes', [])
    no = poly_ob.get('no', [])
    if yes: poly_yes_ask = float(yes[0]['price'])
    if no: poly_no_ask = float(no[0]['price'])
    
    # Kalshi Asks
    k_ticker = kalshi_market.get('ticker')
    k_ob = kalshi.get_market_orderbook(k_ticker)
    if not k_ob: return
    
    # Kalshi orderbook structure: {'yes': [[price, size], ...], 'no': [[price, size], ...]}
    # Prices on Kalshi are often in cents (e.g. 65 means 0.65)
    k_yes_asks = k_ob.get('yes', [])
    k_no_asks = k_ob.get('no', [])
    
    if not k_yes_asks or not k_no_asks: return
    
    # Kalshi prices are 0-100, convert to 0-1
    k_yes_ask = float(k_yes_asks[0][0]) / 100
    k_no_ask = float(k_no_asks[0][0]) / 100
    
    # Scenario A: Buy Polymarket YES, Buy Kalshi NO
    if poly_yes_ask is not None:
        total = poly_yes_ask + k_no_ask
        if total < 1 - (MIN_PROFIT_PCT / 100):
            print_cross_arb(poly_market['question'], "Polymarket YES", poly_yes_ask, "Kalshi NO", k_no_ask, total)
            
    # Scenario B: Buy Kalshi YES, Buy Polymarket NO
    if poly_no_ask is not None:
        total = k_yes_ask + poly_no_ask
        if total < 1 - (MIN_PROFIT_PCT / 100):
            print_cross_arb(poly_market['question'], "Kalshi YES", k_yes_ask, "Polymarket NO", poly_no_ask, total)

def print_cross_arb(q, s1, p1, s2, p2, total):
    profit_pct = (1 - total) * 100
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✈️  CROSS-PLATFORM ARBITRAGE FOUND!")
    print(f"Market: {q}")
    print(f"Buy {s1} @ ${p1:.3f} + Buy {s2} @ ${p2:.3f} = ${total:.3f}")
    print(f"Profit: {profit_pct:.2f}%")
    print("-" * 60)

def fetch_active_markets():
    """Fetch all active binary and multi-outcome markets."""
    url = f"{GAMMA_API_URL}/markets"
    params = {
        "active": "true",
        "closed": "false",
        "limit": 1000,
        "order_by": "volume24hr",
        "order_direction": "desc"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        markets = resp.json()
        for m in markets:
            markets_cache[m['id']] = m
        return markets
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

def fetch_orderbook(market_id):
    """Fetch current order book for a market via Gamma API."""
    url = f"{GAMMA_API_URL}/markets/{market_id}/orderbook"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def check_arbitrage(market, ob):
    """Check for arbitrage opportunities on a single market."""
    if not ob:
        return

    question = market.get('question', 'Unknown')
    slug = market.get('slug', '')
    
    # Use Gamma Orderbook structure
    yes = ob.get('yes', [])
    no = ob.get('no', [])
    outcomes = ob.get('outcomes', [])

    # Scenario 1: Binary market (YES/NO)
    if (yes or no) and not outcomes:
        try:
            y_ask = float(yes[0]['price']) if yes else None
            n_ask = float(no[0]['price']) if no else None
            
            if y_ask and n_ask:
                total = y_ask + n_ask
                if total < 1 - (MIN_PROFIT_PCT / 100):
                    profit_pct = (1 - total) * 100
                    print_arbitrage(question, "YES + NO", total, profit_pct, slug)
        except Exception:
            pass
            
    # Scenario 2: Multi-outcome market (Categorical)
    elif outcomes:
        try:
            total_sum = 0
            details = []
            
            # Polymarket categorical markets: sum of YES for all outcomes must be 1.0
            for outcome in outcomes:
                # In Gamma orderbook, each outcome has its own 'bids' and 'asks'
                asks = outcome.get('asks', [])
                if asks:
                    price = float(asks[0]['price'])
                    total_sum += price
                    details.append(f"{outcome.get('name')}: {price:.3f}")
                else:
                    # If any outcome is missing an ask price, we can't guarantee arbitrage
                    return
            
            if total_sum < 1 - (MIN_PROFIT_PCT / 100):
                profit_pct = (1 - total_sum) * 100
                print_multi_arbitrage(question, total_sum, profit_pct, details, slug)
        except Exception:
            pass

def print_arbitrage(q, type_name, total, profit, slug):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔥 ARBITRAGE FOUND ({type_name})!")
    print(f"Market: {q}")
    print(f"Total Cost: ${total:.3f} | Potential Profit: {profit:.2f}%")
    print(f"Link: https://polymarket.com/event/{slug}")
    print("-" * 60)

def print_multi_arbitrage(q, total, profit, details, slug):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚨 MULTI-OUTCOME ARBITRAGE FOUND!")
    print(f"Market: {q}")
    print(f"Details: {', '.join(details)}")
    print(f"Total Cost: ${total:.3f} | Potential Profit: {profit:.2f}%")
    print(f"Link: https://polymarket.com/event/{slug}")
    print("-" * 60)

def main_loop():
    print("Starting Polymarket Real-Time Arbitrage Scanner...")
    print(f"Platforms: Polymarket + Kalshi (Cross-Arb Enabled)")
    print(f"Min profit: {MIN_PROFIT_PCT}%, Min volume: ${MIN_VOLUME_24H:,}\n")
    
    while True:
        try:
            # 1. Fetch data from both platforms
            p_markets = fetch_active_markets()
            k_markets = kalshi.fetch_active_markets()
            
            p_active = [m for m in p_markets if float(m.get('volume24hr', 0)) >= MIN_VOLUME_24H][:MAX_MARKETS]
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(p_active)} Poly markets vs {len(k_markets)} Kalshi markets...")
            
            for market in p_active:
                # Polling Order Book
                ob = fetch_orderbook(market['id'])
                if not ob: continue
                
                # Check pure arbitrage (YES+NO < 1) on Polymarket
                check_arbitrage(market, ob)
                
                # Check cross-platform arbitrage (Poly vs Kalshi)
                k_match = find_kalshi_match(market.get('question'), k_markets)
                if k_match:
                    check_cross_platform_arb(market, ob, k_match)
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nScanner stopped.")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main_loop()
