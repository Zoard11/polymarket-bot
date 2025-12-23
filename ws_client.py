import json
import threading
import websocket
import time

class PolyWebSocket:
    """
    Manages a persistent WebSocket connection to Polymarket.
    Updates an in-memory orderbook cache in real-time.
    """
    def __init__(self):
        self.ws_url = "wss://ws-live-data.polymarket.com"
        self.orderbooks = {} # {asset_id: orderbook}
        self.last_update = {} # {asset_id: timestamp}
        self.active_subscriptions = [] # To resubscribe after disconnect
        self.ws = None
        self.thread = None

    def on_message(self, ws, message):
        data = json.loads(message)
        now = time.time()
        # Handle CLOB book updates
        if isinstance(data, list):
            for item in data:
                if item.get('event_type') == 'book':
                    asset_id = item.get('asset_id')
                    self.orderbooks[asset_id] = item
                    self.last_update[asset_id] = now
        elif data.get('event_type') == 'book':
            asset_id = data.get('asset_id')
            self.orderbooks[asset_id] = data
            self.last_update[asset_id] = now

    def on_error(self, ws, error):
        print(f"WS Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("### WS Closed - Reconnecting in 5s ###")
        time.sleep(5)
        self.start()

    def on_open(self, ws):
        print("### WS Opened ###")
        # Automatic Resubscription
        if self.active_subscriptions:
            print(f"🔄 Resubscribing to {len(self.active_subscriptions)} markets...")
            self.subscribe(self.active_subscriptions)

    def subscribe(self, asset_ids):
        """Subscribe to orderbook updates for specific assets."""
        self.active_subscriptions = asset_ids # Store for reconnects
        payload = {
            "type": "subscribe",
            "market_ids": asset_ids,
            "channels": ["orderbook"]
        }
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.send(json.dumps(payload))

    def is_fresh(self, asset_id, max_age_sec=60):
        """Check if cached data for this asset is recent."""
        last = self.last_update.get(asset_id, 0)
        return (time.time() - last) < max_age_sec

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

# Singleton instance
poly_ws = PolyWebSocket()
