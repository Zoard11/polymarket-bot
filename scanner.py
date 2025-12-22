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
POLL_INTERVAL = 30  # Increased for NLP overhead
MAX_P_MARKETS = 100           
MAX_K_MARKETS = 1000          

# Global Instances
poly = PolyClient()
kalshi = KalshiClient()
nlp_model = None

def get_nlp_model():
    global nlp_model
    if nlp_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading NLP Model (all-MiniLM-L6-v2) for high-accuracy matching...")
            nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"NLP model loading failed: {e}")
    return nlp_model

def parse_p(p_str):
    """Convert Polymarket cents (ints/strings) to dollars."""
    try: return float(p_str) / 100.0
    except: return None

def find_kalshi_match_semantic(poly_market, kalshi_markets, k_embeddings=None):
    """Use Ticker overlap + Semantic similarity (NLP) to match markets."""
    poly_slug = poly_market.get('slug', '').lower()
    poly_question = poly_market.get('question', '').lower()
    
    # 1. Fast path: ticker/slug overlap
    for km in kalshi_markets:
        k_ticker = (km.get('ticker') or km.get('event_ticker', '')).lower()
        if poly_slug and k_ticker and (poly_slug in k_ticker or k_ticker in poly_slug):
            return km  
    
    # 2. Semantic Fallback (NLP)
    model = get_nlp_model()
    if model is None or k_embeddings is None: return None
    
    try:
        from sentence_transformers import util
        p_emb = model.encode(poly_question, convert_to_tensor=True)
        # Cosine similarity
        hits = util.cos_sim(p_emb, k_embeddings)[0]
        best_idx = hits.argmax()
        if hits[best_idx] > 0.82: # High threshold for high confidence
            return kalshi_markets[best_idx]
    except: pass
    
    return None

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
    # 1. Poly Asks
    yes_list = poly_ob.get('yes', [])
    no_list = poly_ob.get('no', [])
    
    p_yes_best = min(yes_list, key=lambda x: float(x['price'])) if yes_list else None
    p_no_best = min(no_list, key=lambda x: float(x['price'])) if no_list else None
    
    if not p_yes_best or not p_no_best: return
    p_yes_ask = parse_p(p_yes_best['price'])
    p_no_ask = parse_p(p_no_best['price'])
    
    # 2. Kalshi Asks
    k_data = kalshi.get_market_orderbook(kalshi_market.get('ticker'))
    if not k_data: return
    
    k_yes = k_data.get('yes_ask')
    k_no = k_data.get('no_ask')
    if not k_yes or not k_no: return
    
    k_yes_ask = float(k_yes[0]) / 100.0
    k_no_ask = float(k_no[0]) / 100.0
    
    # 3. Arbitrage Checks
    # Poly YES + Kalshi NO
    total_a = p_yes_ask + k_no_ask
    if total_a < 1 - (MIN_PROFIT_PCT / 100):
        if (p_yes_ask * float(p_yes_best.get('size', 0)) >= MIN_LIQUIDITY_USD and 
            k_no_ask * float(k_no[1]) >= MIN_LIQUIDITY_USD):
            print_alert("CROSS (Poly YES + Kalshi NO)", poly_market['question'], total_a, (1-total_a)*100, poly_market['slug'])

    # Kalshi YES + Poly NO
    total_b = k_yes_ask + p_no_ask
    if total_b < 1 - (MIN_PROFIT_PCT / 100):
        if (k_yes_ask * float(k_yes[1]) >= MIN_LIQUIDITY_USD and 
            p_no_ask * float(p_no_best.get('size', 0)) >= MIN_LIQUIDITY_USD):
            print_alert("CROSS (Kalshi YES + Poly NO)", poly_market['question'], total_b, (1-total_b)*100, poly_market['slug'])

def print_alert(type_name, q, total, profit, slug, details=None):
    icon = "🔥" if "CROSS" not in type_name else "🌐"
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {icon} {type_name} ARBITRAGE FOUND!")
    print(f"Market: {q}")
    if details: print(f"Details: {', '.join(details)}")
    print(f"Total Cost: ${total:.3f} | Profit: {profit:.2f}%")
    print(f"Link: https://polymarket.com/event/{slug}")
    print("-" * 60)

def main():
    parser = argparse.ArgumentParser(description="Polymarket & Kalshi NLP Arbitrage Scanner")
    parser.add_argument("--once", action="store_true", help="Run the scan once and exit")
    args = parser.parse_args()

    print("Polymarket & Kalshi Arbitrage Scanner (Advanced NLP Mode)")
    print(f"Settings: Min Profit {MIN_PROFIT_PCT}%, Min Liquidity ${MIN_LIQUIDITY_USD}\n")
    
    model = get_nlp_model()
    
    while True:
        try:
            p_active = poly.fetch_active_markets(MIN_VOLUME_24H, MAX_P_MARKETS)
            k_active = kalshi.fetch_active_markets(MAX_K_MARKETS)
            
            # Pre-compute Kalshi embeddings
            k_embeddings = None
            if model and k_active:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Encoding {len(k_active)} Kalshi markets...")
                k_texts = [(km.get('title', '') + " " + km.get('subtitle', '')).lower() for km in k_active]
                k_embeddings = model.encode(k_texts, convert_to_tensor=True)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(p_active)} Poly vs {len(k_active)} Kalshi...")
            
            for market in p_active:
                ob = poly.get_orderbook(market['id'])
                if not ob: continue
                
                check_arbitrage(market, ob)
                
                # Semantic NLP Match
                k_match = find_kalshi_match_semantic(market, k_active, k_embeddings)
                if k_match:
                    check_cross_platform_arb(market, ob, k_match)
            
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
