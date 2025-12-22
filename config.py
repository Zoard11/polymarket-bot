# Arbitrage Scanner Configuration
# All percentages are in decimal (0.01 = 1%)

# Profitability
MIN_PROFIT_PCT = 1.0          # Minimum NET profit after fees
FEE_PCT = 0.5                 # Estimated fees/slippage buffer per platform (Total ~1.0%)

# Execution Simulation
# We calculate arbitrage based on this trade size to account for slippage
TARGET_TRADE_SIZE_USD = 200   

# Market Filtering
MIN_VOLUME_24H = 10000        # Minimum market volume to consider
MIN_LIQUIDITY_USD = 100       # Minimum liquidity at the best price

# Hardware / Performance
POLL_INTERVAL_POLY = 15       # Fast polling for internal arbs
POLL_INTERVAL_CROSS = 30      # Slower for NLP model overhead
MAX_P_MARKETS = 150           
MAX_K_MARKETS = 1000          

# NLP Settings
NLP_MATCH_THRESHOLD = 0.82    # Cosine similarity for high-confidence matches
