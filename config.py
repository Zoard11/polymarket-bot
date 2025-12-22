# Arbitrage Scanner Configuration
# All percentages are in decimal (0.01 = 1%)

# Profitability
MIN_PROFIT_PCT = 1.0          # Minimum NET profit after fees
FEE_PCT = 0.5                 # Estimated fees/slippage buffer per platform (Total ~1.0%)

# Execution Simulation
# We calculate arbitrage based on this trade size to account for slippage
TARGET_TRADE_SIZE_USD = 200   

# Risk Management
MAX_EXPOSURE_PER_MARKET_USD = 1000  # Cap on total position size
MAX_TOTAL_OPEN_TRADES = 5          # Number of concurrent arbs to track
MIN_MARKET_AGE_HOURS = 1           # Avoid brand new, ultra-volatile markets

# Statistical Modeling / Volatility
# Adjust profit threshold based on 24h volume/volatility proxies
VOLATILITY_ADJUSTMENT_ENABLED = True
HIGH_VOL_PROFIT_BUFFER = 0.5       # Add 0.5% buffer to threshold for high-vol markets

# Robustness
API_MAX_RETRIES = 3
API_RETRY_DELAY = 5                # Seconds between retries
