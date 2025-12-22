import json
import threading
import websocket
import time

class PolyWebSocket:
    """
    Manages a persistent WebSocket connection to Polymarket CLOB.
    Updates an in-memory orderbook cache in real-time.
    """
    def __init__(self):
        self.ws_url = "wss://clob.polymarket.com/ws"
        self.orderbooks = {} # {asset_id: orderbook}
        self.ws = None
        self.thread = None

    def on_message(self, ws, message):
        data = json.loads(message)
        # Handle CLOB book updates
        if isinstance(data, list):
            for item in data:
                if item.get('event_type') == 'book':
                    asset_id = item.get('asset_id')
                    self.orderbooks[asset_id] = item
        elif data.get('event_type') == 'book':
            asset_id = data.get('asset_id')
            self.orderbooks[asset_id] = data

    def on_error(self, ws, error):
        print(f"WS Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("### WS Closed ###")
        time.sleep(5)
        self.start()

    def on_open(self, ws):
        print("### WS Opened ###")

    def subscribe(self, asset_ids):
        """Subscribe to orderbook updates for specific assets."""
        payload = {
            "type": "subscribe",
            "assets_ids": asset_ids,
            "channels": ["book"]
        }
        self.ws.send(json.dumps(payload))

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
