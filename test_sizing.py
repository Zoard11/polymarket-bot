import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

import config
from trade_executor import TradeExecutor

def test_sizing():
    executor = TradeExecutor()
    
    # Mock market object
    market = {"question": "Test Market Sizing"}
    
    print("--- Testing Default Sizing ($10) ---")
    executor.place_maker_orders(market, 0.45, 0.50)
    
    print("\n--- Testing Small Sizing (Below Min $5) ---")
    executor.place_maker_orders(market, 0.45, 0.50, size_usd=4.0)
    
    print("\n--- Testing Custom Sizing ($30) ---")
    executor.place_maker_orders(market, 0.45, 0.50, size_usd=30.0)

if __name__ == "__main__":
    test_sizing()
