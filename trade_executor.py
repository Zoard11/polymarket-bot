import logging
import os
import config
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account
from py_clob_client.client import ClobClient, ApiCreds
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import OrderArgs, OrderType

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
        self.active_orders = {}  # Track open orders
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
        
        # LOGGING
        print(f"\n[{timestamp}] 🤖 [EXECUTION ALERT] ---------------------------------")
        print(f"[{timestamp}] 🤖 Target: {market.get('question')}")
        print(f"[{timestamp}] 🤖 Plan: BUY {shares_yes} YES @ {y_bid:.3f} | BUY {shares_no} NO @ {n_bid:.3f}")
        print(f"[{timestamp}] 🤖 Spread Profit: ${(1.0 - (y_bid + n_bid))*100:.2f}%")

        if not getattr(config, 'LIVE_TRADING', False):
            print(f"[{timestamp}] 🛑 ACTUAL TRADING DISABLED (Config.LIVE_TRADING = False)")
            print(f"[{timestamp}] 🤖 [MOCK-ONLY] Order NOT Sent.")
            print(f"[{timestamp}] 🤖 ---------------------------------------------\n")
            return

        # EXECUTE REAL TRADES
        if not self.clob:
            print(f"[{timestamp}] ❌ Error: CLOB Client not initialized. Cannot trade.")
            return

        try:
            # Parse Token IDs from Market Object
            import json
            tids = market.get('clobTokenIds')
            if isinstance(tids, str):
                tids = json.loads(tids)
            
            if not tids or len(tids) < 2:
                print(f"[{timestamp}] ❌ Error: Missing Token IDs in market data.")
                return

            yes_token = tids[0]
            no_token = tids[1]

            # Prepare Orders
            order_yes = OrderArgs(price=float(f"{y_bid:.3f}"), size=int(shares_yes), side="BUY", token_id=yes_token)
            order_no = OrderArgs(price=float(f"{n_bid:.3f}"), size=int(shares_no), side="BUY", token_id=no_token)

            print(f"[{timestamp}] ⚠️ Submitting Order A (YES)...")
            resp_a = self.clob.create_order(order_yes)
            
            if not resp_a.get('success'):
                print(f"[{timestamp}] ❌ Order A (YES) Failed: {resp_a.get('error') or resp_a}")
                print(f"[{timestamp}] ✋ Order B (NO) was NOT attempted for safety.")
                return

            order_id_a = resp_a.get('orderID')
            print(f"[{timestamp}] ✅ Order A (YES) Submitted: ID {order_id_a}")

            print(f"[{timestamp}] ⚠️ Submitting Order B (NO)...")
            resp_b = self.clob.create_order(order_no)

            if not resp_b.get('success'):
                error_msg = resp_b.get('error') or resp_b
                print(f"[{timestamp}] ❌ Order B (NO) Failed: {error_msg}")
                print(f"[{timestamp}] 🔄 INITIATING ROLLBACK: Attempting to cancel Order A...")
                
                try:
                    cancel_resp = self.clob.cancel(order_id_a)
                    if cancel_resp and cancel_resp.get('canceled'):
                        print(f"[{timestamp}] 🛡️ ROLLBACK SUCCESSFUL: Order A ({order_id_a}) was cancelled.")
                    else:
                        print(f"[{timestamp}] 🚨 ROLLBACK FAILED: Order A might have filled! UNHEDGED EXPOSURE DETECTED.")
                except Exception as ex:
                    print(f"[{timestamp}] 🚨 ROLLBACK CRASHED: {ex}. UNHEDGED EXPOSURE DETECTED.")
            else:
                print(f"[{timestamp}] ✅ Order B (NO) Submitted: ID {resp_b.get('orderID')}")
                print(f"[{timestamp}] 🎉 SUCCESS: Hedge cycle complete (YES + NO balanced).")

        except Exception as e:
            print(f"[{timestamp}] ❌ Order Execution Failed: {e}")
        
        print(f"[{timestamp}] 🤖 ---------------------------------------------\n")
