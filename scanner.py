import requests
import json
import time
from datetime import datetime
# Polymarket Gamma API
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# Configuration
MIN_PROFIT_PCT = 1.0          # Only show opportunities > 1% profit
MIN_VOLUME_24H = 50000        # Only scan markets with > $50k volume (in USD)
POLL_INTERVAL = 10            # Seconds between full scans
MAX_MARKETS = 50              # Max markets to scan per cycle

# Global state
markets_cache = {}

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
    print("Starting Polymarket Real-Time Arbitrage Scanner (Optimized Polling)...")
    print(f"Min profit: {MIN_PROFIT_PCT}%, Min volume: ${MIN_VOLUME_24H:,}\n")
    
    while True:
        try:
            markets = fetch_active_markets()
            active_list = [m for m in markets if float(m.get('volume24hr', 0)) >= MIN_VOLUME_24H][:MAX_MARKETS]
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(active_list)} high-volume markets...")
            
            for market in active_list:
                # Fetch full orderbook to get real Bid/Ask
                ob = fetch_orderbook(market['id'])
                if ob:
                    check_arbitrage(market, ob)
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nScanner stopped.")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main_loop()
