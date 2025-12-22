# Arbitrage Scanner Configuration
# All percentages are in decimal (0.01 = 1%)

BANKROLL_USD = 10000          # Simulated total capital for sizing calculations

# Profitability
MIN_PROFIT_PCT = 1.0          # Minimum NET profit after fees
FEE_PCT = 0.5                 # Estimated fees/slippage buffer per platform (Total ~1.0%)

# Execution Simulation
# Fallback size if sizing logic fails
TARGET_TRADE_SIZE_USD = 200   

# Risk Management
MAX_EXPOSURE_PER_MARKET_USD = 1000  # Cap on total position size
MAX_TOTAL_OPEN_TRADES = 5          # Number of concurrent arbs to track
MIN_MARKET_AGE_HOURS = 1           # Avoid brand new, ultra-volatile markets
KELLY_FRACTION = 0.2               # Use 20% of the recommended Kelly size (Conservative Fractional Kelly)
MAX_EVENT_EXPOSURE_USD = 2500      # Cumulative exposure across all platforms for one event

# Statistical Modeling / Volatility
# Adjust profit threshold based on 24h volume/volatility proxies
VOLATILITY_ADJUSTMENT_ENABLED = True
HIGH_VOL_PROFIT_BUFFER = 0.5       # Add 0.5% buffer to threshold for high-vol markets

# Robustness
API_MAX_RETRIES = 3
API_RETRY_DELAY = 5                # Seconds between retries

# Scanner Settings
MIN_VOLUME_24H = 10000             # Minimum 24h volume for a market to be considered
MAX_P_MARKETS = 200                # Max Polymarket events to fetch per cycle
POLL_INTERVAL_POLY = 15            # Seconds between Polymarket scans

# Cross-Platform Settings
MAX_K_MARKETS = 300                # Max active Kalshi markets to fetch
POLL_INTERVAL_CROSS = 60           # Seconds between cross-platform scans
NLP_MATCH_THRESHOLD = 0.82         # Minimum cosine similarity for semantic matching
