import time
import sys
import argparse
import json
from datetime import datetime
from poly_client import PolyClient
from kalshi_client import KalshiClient
import config
from risk_manager import risk_manager

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

def load_manual_mapping():
    try:
        with open('market_mapping.json', 'r') as f:
            return json.load(f)
    except: return {}

def parse_p(p_str):
    try:
        val = float(p_str)
        if val > 1.0: return val / 100.0
        return val
    except: return None

def calculate_kelly_size(profit_pct):
    if profit_pct <= 0: return config.TARGET_TRADE_SIZE_USD
    size = config.BANKROLL_USD * (profit_pct / 100) * config.KELLY_FRACTION * 10
    return max(config.TARGET_TRADE_SIZE_USD, min(size, config.MAX_EXPOSURE_PER_MARKET_USD))

def get_vwap_price(order_list, target_usd, is_kalshi=False):
    if not order_list: return None
    total_spent = 0
    total_qty = 0
    normalized = []
    for o in order_list:
        if is_kalshi: normalized.append({'p': float(o[0]) / 100.0, 's': float(o[1])})
        else: normalized.append({'p': parse_p(o['price']), 's': float(o.get('size', 0))})
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

def find_kalshi_match_semantic(poly_market, kalshi_markets, k_embeddings=None, mapping=None):
    poly_slug = poly_market.get('slug', '').lower()
    poly_question = poly_market.get('question', '').lower()
    
    # 0. Manual Mapping Override (Highest Priority)
    if mapping and poly_slug in mapping:
        k_ticker = mapping[poly_slug]
        for km in kalshi_markets:
            if (km.get('ticker') or km.get('event_ticker', '')) == k_ticker:
                return km

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
        hits = util.cos_sim(p_emb, k_embeddings)[0]
        best_idx = hits.argmax()
        if hits[best_idx] > config.NLP_MATCH_THRESHOLD:
            return kalshi_markets[best_idx]
    except: pass
    return None

def check_cross_platform_arb(poly_market, poly_ob, kalshi_market):
    fee_multiplier = 1 + (config.FEE_PCT / 100)
    target_leg = config.TARGET_TRADE_SIZE_USD / 2
    
    # Dynamic Threshold based on Poly Volume
    volume = float(poly_market.get('volume24hr', 0))
    min_profit = config.MIN_PROFIT_PCT
    if config.VOLATILITY_ADJUSTMENT_ENABLED and volume < 50000:
        min_profit += config.HIGH_VOL_PROFIT_BUFFER

    p_yes_vwap = get_vwap_price(poly_ob.get('yes', []), target_leg)
    p_no_vwap = get_vwap_price(poly_ob.get('no', []), target_leg)
    
    k_ob = kalshi.get_market_orderbook(kalshi_market.get('ticker'))
    if not k_ob: return
    
    k_yes_vwap = get_vwap_price(k_ob.get('yes', []), target_leg, is_kalshi=True)
    k_no_vwap = get_vwap_price(k_ob.get('no', []), target_leg, is_kalshi=True)
    
    if p_yes_vwap and k_no_vwap:
        total = (p_yes_vwap + k_no_vwap) * fee_multiplier
        if total < 1 - (min_profit / 100):
            profit = (1 - total) * 100
            rec_size = calculate_kelly_size(profit)
            can_add, reason = risk_manager.can_add_position(poly_market['slug'], poly_market['slug'], rec_size)
            risk_msg = "" if can_add else f" [RISK WARNING: {reason}]"
            print_alert("CROSS (Poly YES + Kalshi NO)", poly_market['question'], total, profit, poly_market['slug'], size=rec_size, risk_msg=risk_msg)

    if k_yes_vwap and p_no_vwap:
        total = (k_yes_vwap + p_no_vwap) * fee_multiplier
        if total < 1 - (min_profit / 100):
            profit = (1 - total) * 100
            rec_size = calculate_kelly_size(profit)
            can_add, reason = risk_manager.can_add_position(poly_market['slug'], poly_market['slug'], rec_size)
            risk_msg = "" if can_add else f" [RISK WARNING: {reason}]"
            print_alert("CROSS (Kalshi YES + Poly NO)", poly_market['question'], total, profit, poly_market['slug'], size=rec_size, risk_msg=risk_msg)

def print_alert(type_name, q, total, profit, slug, size=0, risk_msg=""):
    alert_text = f"\n[{datetime.now().strftime('%H:%M:%S')}] [CROSS] 🌐 {type_name} ARBITRAGE FOUND!{risk_msg}\n"
    alert_text += f"Market: {q}\n"
    alert_text += f"Total Cost (Net): ${total:.3f} | Profit: {profit:.2f}%\n"
    alert_text += f"Recommended Size: ${size:,.0f} (Kelly)\n"
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

    print("Cross-Platform NLP Arbitrage Scanner (Professional Suite)")
    mapping = load_manual_mapping()
    if mapping: print(f"Loaded {len(mapping)} manual market overrides.")
    
    model = get_nlp_model()
    
    while True:
        try:
            p_active = poly.fetch_active_markets(config.MIN_VOLUME_24H, config.MAX_P_MARKETS)
            k_active = kalshi.fetch_active_markets(config.MAX_K_MARKETS)
            
            k_embeddings = None
            if model and k_active:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Encoding {len(k_active)} markets...")
                k_texts = [(km.get('title', '') + " " + km.get('subtitle', '')).lower() for km in k_active]
                k_embeddings = model.encode(k_texts, convert_to_tensor=True)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring {len(p_active)} Poly vs {len(k_active)} Kalshi...")
            for market in p_active:
                ob = poly.get_market_orderbooks(market)
                if not ob: continue
                k_match = find_kalshi_match_semantic(market, k_active, k_embeddings, mapping)
                if k_match: check_cross_platform_arb(market, ob, k_match)
            
            if args.once: break
            time.sleep(config.POLL_INTERVAL_CROSS)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
