import time
import sys
import argparse
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient
import config

# Global Instances
poly = PolyClient()
kalshi = KalshiClient()
nlp_model = None

def get_nlp_model():
    global nlp_model
    if nlp_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading NLP Model (all-MiniLM-L6-v2) for matching...")
            nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"NLP model loading failed: {e}")
    return nlp_model

def parse_p(p_str):
    """Convert Polymarket/Kalshi cents to dollars."""
    try: return float(p_str) / 100.0
    except: return None

def get_vwap_price(order_list, target_usd, is_kalshi=False):
    """Calculate the average price to fill target_usd. order_list: [[p, s], ...] for Kalshi or [{'price': p, 'size': s}] for Poly."""
    if not order_list: return None
    
    total_spent = 0
    total_qty = 0
    
    # Normalize order list to [{'p': float_price, 's': float_size}]
    normalized = []
    for o in order_list:
        if is_kalshi:
            normalized.append({'p': float(o[0]) / 100.0, 's': float(o[1])})
        else:
            normalized.append({'p': parse_p(o['price']), 's': float(o.get('size', 0))})
            
    # Sort by price (low to high)
    sorted_orders = sorted(normalized, key=lambda x: x['p'])
    
    for order in sorted_orders:
        price = order['p']
        size = order['s']
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

def find_kalshi_match_semantic(poly_market, kalshi_markets, k_embeddings=None):
    """Use Ticker overlap + Semantic similarity (NLP) to match markets."""
    poly_slug = poly_market.get('slug', '').lower()
    poly_question = poly_market.get('question', '').lower()
    
    for km in kalshi_markets:
        k_ticker = (km.get('ticker') or km.get('event_ticker', '')).lower()
        if poly_slug and k_ticker and (poly_slug in k_ticker or k_ticker in poly_slug):
            return km  
    
    model = get_nlp_model()
    if model is None or k_embeddings is None: return None
    
    try:
        from sentence_transformers import util
        p_emb = model.encode(poly_question, convert_to_tensor=True)
        hits = util.cos_sim(p_emb, k_embeddings)[0]
        best_idx = hits.argmax()
        if hits[best_idx] > config.NLP_MATCH_THRESHOLD:
            return kalshi_markets[best_idx]
    except: pass
    return None

def check_cross_platform_arb(poly_market, poly_ob, kalshi_market):
    """Check for arbitrage between Polymarket and Kalshi using VWAP and Fees."""
    fee_multiplier = 1 + (config.FEE_PCT / 100)
    target_leg = config.TARGET_TRADE_SIZE_USD / 2

    # 1. Poly Prices (Asks)
    p_yes_vwap = get_vwap_price(poly_ob.get('yes', []), target_leg)
    p_no_vwap = get_vwap_price(poly_ob.get('no', []), target_leg)
    
    # 2. Kalshi Prices (Asks)
    k_ob = kalshi.get_market_orderbook(kalshi_market.get('ticker'))
    if not k_ob: return
    
    k_yes_vwap = get_vwap_price(k_ob.get('yes', []), target_leg, is_kalshi=True)
    k_no_vwap = get_vwap_price(k_ob.get('no', []), target_leg, is_kalshi=True)
    
    # 3. Arbitrage Checks
    # Poly YES + Kalshi NO
    if p_yes_vwap and k_no_vwap:
        total_a = (p_yes_vwap + k_no_vwap) * fee_multiplier
        if total_a < 1 - (config.MIN_PROFIT_PCT / 100):
            print_alert("CROSS (Poly YES + Kalshi NO)", poly_market['question'], total_a, (1-total_a)*100, poly_market['slug'])

    # Kalshi YES + Poly NO
    if k_yes_vwap and p_no_vwap:
        total_b = (k_yes_vwap + p_no_vwap) * fee_multiplier
        if total_b < 1 - (config.MIN_PROFIT_PCT / 100):
            print_alert("CROSS (Kalshi YES + Poly NO)", poly_market['question'], total_b, (1-total_b)*100, poly_market['slug'])

def print_alert(type_name, q, total, profit, slug, details=None):
    icon = "🌐"
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

def main():
    parser = argparse.ArgumentParser(description="Cross-Platform NLP Arbitrage Scanner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print("Cross-Platform NLP Arbitrage Scanner (Professional Mode)")
    print(f"Settings: Target Size ${config.TARGET_TRADE_SIZE_USD}, Min Net {config.MIN_PROFIT_PCT}%\n")
    
    model = get_nlp_model()
    
    while True:
        try:
            p_active = poly.fetch_active_markets(config.MIN_VOLUME_24H, config.MAX_P_MARKETS)
            k_active = kalshi.fetch_active_markets(config.MAX_K_MARKETS)
            
            k_embeddings = None
            if model and k_active:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Encoding {len(k_active)} Kalshi markets...")
                k_texts = [(km.get('title', '') + " " + km.get('subtitle', '')).lower() for km in k_active]
                k_embeddings = model.encode(k_texts, convert_to_tensor=True)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring {len(p_active)} Poly vs {len(k_active)} Kalshi...")
            
            for market in p_active:
                ob = poly.get_orderbook(market['id'])
                if not ob: continue
                
                # Semantic NLP Match
                k_match = find_kalshi_match_semantic(market, k_active, k_embeddings)
                if k_match:
                    check_cross_platform_arb(market, ob, k_match)
            
            if args.once: break
            time.sleep(config.POLL_INTERVAL_CROSS)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
