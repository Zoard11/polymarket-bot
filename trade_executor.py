import logging
import os
import config
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account
from py_clob_client.client import ClobClient, ApiCreds
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import OrderArgs, OrderType
from risk_manager import risk_manager

# Setup specific logger for trades
logger = logging.getLogger('executor')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

load_dotenv()

class TradeExecutor:
    def __init__(self, poly_client=None):
        self.poly = poly_client  # Standard HTTP/Gamma Client
        self.clob = None         # Authenticated L2 Client
        self.active_orders = {}  # Format: {order_id: {"market": m, "side": s, ...}}
        self.hedge_pairs = []    # Format: [{"yes_id": id1, "no_id": id2, "market": m, "time": t, "size": s}]
        self._init_clob()

    def _init_clob(self):
        """Initialize the Authenticated CLOB Client using L2 Keys."""
        try:
            host = "https://clob.polymarket.com"
            key = (os.getenv("PRIVATE_KEY") or os.getenv("PRVATE_KEY") or "").strip()
            api_key = (os.getenv("POLY_API_KEY") or "").strip()
            secret = (os.getenv("POLY_API_SECRET") or "").strip()
            passphrase = (os.getenv("POLY_API_PASSPHRASE") or "").strip()
            proxy_addr = (os.getenv("POLY_PROXY_ADDRESS") or "").strip()
            chain_id = POLYGON

            if not api_key or not secret or not passphrase or not proxy_addr:
                logger.warning("⚠️ TradeExecutor: Missing API Credentials/Proxy in .env. Running in READ-ONLY Mode.")
                return

            creds = ApiCreds(
                api_key=api_key,
                api_secret=secret,
                api_passphrase=passphrase
            )

            client_args = {
                "host": host,
                "key": key, 
                "chain_id": chain_id,
                "creds": creds,
                "signature_type": 1,
                "funder": proxy_addr
            }
            
            self.clob = ClobClient(**client_args)
            logger.info("✅ TradeExecutor: CLOB Client Authenticated Successfully.")
            
        except Exception as e:
            logger.error(f"❌ TradeExecutor Init Failed: {e}")

    def place_maker_orders(self, market, y_bid, n_bid, size_usd=None):
        """
        Places Limit Buy Orders on both sides to capture the spread.
        Uses Real API if LIVE_TRADING is True.
        """
        if size_usd is None:
            size_usd = getattr(config, 'MAKER_TRADE_SIZE_USD', config.TARGET_TRADE_SIZE_USD)
            
        # Check against safety floor
        min_size = getattr(config, 'MIN_TRADE_SIZE_USD', 5.0)
        if size_usd < min_size:
            logger.warning(f"⚠️ Trade aborted: Target size ${size_usd} is below the floor of ${min_size}.")
            return
            
        # Calculate Sizes
        shares_yes = int((size_usd / 2) / y_bid)
        shares_no = int((size_usd / 2) / n_bid)
        
        timestamp = datetime.now().strftime('%H:%M:%S')

        if not getattr(config, 'LIVE_TRADING', False):
            print(f"\n[{timestamp}] 🤖 [MOCK ALERT] {market.get('question')[:50]}...")
            print(f"[{timestamp}] 🤖 Plan: BUY {shares_yes} YES @ {y_bid:.3f} | BUY {shares_no} NO @ {n_bid:.3f}")
            print(f"[{timestamp}] 🛑 ACTUAL TRADING DISABLED (Config.LIVE_TRADING = False)\n")
            return

        # RISK MANAGER GATE: Check if we have capital and are within limits
        market_id = market.get('conditionId') or market.get('id')
        event_id = market.get('event_slug') or market.get('slug') or 'unknown'
        can_trade, reason = risk_manager.can_add_position(event_id, market_id, size_usd)
        if not can_trade:
            print(f"[{timestamp}] 🛡️ RISK GATE: Trade blocked - {reason}")
            return

        # EXECUTE REAL TRADES (Optimized for Speed)
        if not self.clob:
            print(f"[{timestamp}] ❌ Error: CLOB Client not initialized.")
            return

        try:
            # Fast Token Parsing
            import json
            tids = market.get('clobTokenIds')
            if isinstance(tids, str):
                tids = json.loads(tids)
            
            if not tids or len(tids) < 2: return

            yes_token, no_token = tids[0], tids[1]

            # Immediate Order Placement (Prioritize Speed)
            order_yes = OrderArgs(price=float(f"{y_bid:.3f}"), size=int(shares_yes), side="BUY", token_id=yes_token)
            # Immediate Order Placement (Prioritize Speed)
            # STEP 1: Create and Sign locally
            signed_yes = self.clob.create_order(order_yes)
            # STEP 2: Post to exchange
            resp_a = self.clob.post_order(signed_yes, OrderType.GTC)
            
            if not resp_a.get('success'):
                err = resp_a.get('errorMsg') or resp_a.get('error')
                logger.error(f"[{timestamp}] ❌ Order A Fail: {err}")
                return

            order_id_a = resp_a.get('orderID')
            order_no = OrderArgs(price=float(f"{n_bid:.3f}"), size=int(shares_no), side="BUY", token_id=no_token)
            
            # STEP 1: Create and Sign locally
            signed_no = self.clob.create_order(order_no)
            # STEP 2: Post to exchange
            resp_b = self.clob.post_order(signed_no, OrderType.GTC)

            # LOGGING (Done AFTER orders are sent to reduce latency)
            print(f"\n[{timestamp}] 🚀 [LIVE EXECUTION] {market.get('question')[:50]}...")
            print(f"[{timestamp}] ✅ YES Submitted: {order_id_a}")
            
            if not resp_b.get('success'):
                err_b = resp_b.get('errorMsg') or resp_b.get('error')
                print(f"[{timestamp}] ❌ NO Failed: {err_b}. 🔄 INITIATING ROLLBACK...")
                try:
                    self.clob.cancel(order_id_a)
                    print(f"[{timestamp}] 🛡️ ROLLBACK SUCCESSFUL.")
                except Exception: print(f"[{timestamp}] 🚨 ROLLBACK FAILED!")
            else:
                # Record for Hedge Chaser
                self.hedge_pairs.append({
                    "yes_id": order_id_a,
                    "no_id": resp_b.get('orderID'),
                    "yes_token": yes_token,
                    "no_token": no_token,
                    "size_yes": shares_yes,
                    "size_no": shares_no,
                    "timestamp": datetime.now(),
                    "market_question": market.get('question'),
                    "chased": False
                })

                # Record successful trade in RiskManager for capital tracking
                risk_manager.record_trade(event_id, market_id, size_usd)

    def check_and_chase_hedges(self):
        """
        Loops through active hedge pairs. If one side is filled and the other isn't 
        (after timeout), it cancels the bid and market-buys the missing side.
        """
        if not self.clob or not self.hedge_pairs:
            return

        import time
        now = datetime.now()
        timeout = getattr(config, 'HEDGE_TIMEOUT_SEC', 300)
        
        remaining_pairs = []
        for pair in self.hedge_pairs:
            if pair.get('chased'): continue
            
            try:
                # 1. Check Status of both orders
                status_a = self.clob.get_order(pair['yes_id'])
                status_b = self.clob.get_order(pair['no_id'])
                
                # Check if both are completely filled
                fill_a = float(status_a.get('size_matched', 0)) >= float(status_a.get('original_size', 0))
                fill_b = float(status_b.get('size_matched', 0)) >= float(status_b.get('original_size', 0))

                if fill_a and fill_b:
                    logger.info(f"✅ Hedge Fully Filled: {pair['market_question'][:30]}")
                    continue # Successfully closed!

                # 2. Check for "Hanging" state (One filled, one not) after timeout
                pair_age = (now - pair['timestamp']).total_seconds()
                
                if pair_age > timeout:
                    target_id = None
                    target_token = None
                    target_size = None
                    side_name = ""

                    if fill_a and not fill_b:
                        target_id, target_token, target_size, side_name = pair['no_id'], pair['no_token'], pair['size_no'], "NO"
                    elif fill_b and not fill_a:
                        target_id, target_token, target_size, side_name = pair['yes_id'], pair['yes_token'], pair['size_yes'], "YES"

                    if target_id:
                        logger.warning(f"⚠️ HEDGE HANGING! ({int(pair_age)}s) Chasing {side_name} for '{pair['market_question'][:30]}'")
                        
                        # STEP 1: Cancel the hanging Limit Order
                        try: self.clob.cancel(target_id)
                        except: pass
                        
                        # STEP 2: Place a MARKET ORDER (Aggressive Taker) to close the gap
                        # We use a very high/low price to ensure immediate fill (taking the book)
                        chase_price = 0.99 if side_name == "YES" else 0.99
                        # Technically the CLOB API 'create_market_order' handles this better
                        # but we use a marketable limit order for safety if FOK isn't available
                        chase_args = OrderArgs(price=0.99, size=int(target_size), side="BUY", token_id=target_token)
                        signed_chase = self.clob.create_order(chase_args)
                        resp = self.clob.post_order(signed_chase)
                        
                        if resp.get('success'):
                            logger.info(f"🛡️ CHASE SUCCESSFUL: {side_name} filled via Market Order.")
                            pair['chased'] = True
                            continue
                        else:
                            logger.error(f"🚨 CHASE FAILED: {resp.get('errorMsg')}")

                remaining_pairs.append(pair)
            except Exception as e:
                logger.error(f"❌ Error checking hedge pair: {e}")
                remaining_pairs.append(pair)

        self.hedge_pairs = remaining_pairs
