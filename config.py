# Arbitrage Scanner Configuration
# All percentages are in decimal (0.01 = 1%)

BANKROLL_USD = 10000          # Simulated total capital for sizing calculations

# Profitability
MIN_PROFIT_PCT = 1.0          # Minimum NET profit after fees
FEE_PCT = 0.5                 # Estimated fees/slippage buffer per platform (Total ~1.0%)

# Execution Simulation
# Fallback size if sizing logic fails
# This is split 50/50 between YES and NO sides.
TARGET_TRADE_SIZE_USD = 10.0   
MIN_TRADE_SIZE_USD = 5.0      # Safety floor for reliable Polymarket CLOB execution
                              # Note: Polymarket CLOB API often requires $5.00 for reliable 
                              # execution across all markets. Orders < $5 might be rejected 
                              # by the exchange depending on the specific market's 'min_size'.

# Risk Management
MAX_EXPOSURE_PER_MARKET_USD = 1000  # Cap on total position size
MAX_TOTAL_OPEN_TRADES = 4          # Number of concurrent arbs (Adjusted for $45 bankroll)
MIN_MARKET_AGE_HOURS = 1           # Avoid brand new, ultra-volatile markets
KELLY_FRACTION = 0.2               # Use 20% of the recommended Kelly size (Conservative Fractional Kelly)
MAX_EVENT_EXPOSURE_USD = 2500      # Cumulative exposure across all platforms for one event
STARTING_BANKROLL_USD = 45.0       # Your starting capital. RiskManager will prevent overexposure.

# Statistical Modeling / Volatility
# Adjust profit threshold based on 24h volume/volatility proxies
VOLATILITY_ADJUSTMENT_ENABLED = True
HIGH_VOL_PROFIT_BUFFER = 0.5       # Add 0.5% buffer to threshold for high-vol markets

# Robustness
API_MAX_RETRIES = 3
API_RETRY_DELAY = 5                # Seconds between retries

# Scanner Settings
MIN_VOLUME_24H = 10000             # Minimum 24h volume for standard markets
MAX_P_MARKETS = 200                # Max Polymarket events to fetch per cycle
POLL_INTERVAL_POLY = 15            # Seconds between Polymarket scans
HF_KEYWORDS = ["Up or Down", "15m", "15-minute"] # Keywords to force-include regardless of volume
HF_LIMIT = 50                      # Max high-frequency markets to track

# Maker Strategy Settings
MAKER_TRADE_SIZE_USD = 10.0        # Total per cycle ($5 YES + $5 NO to meet exchange minimums)
MAKER_MIN_PROFIT_PCT = 1.0         # Minimum spread profit to trigger alert (e.g. 1.0%)
MAKER_ALLOW_DEAD_MARKETS = False   # If True, allows markets with 0 bids (Cost=0) -> 100% spread
MAKER_MIN_SIDE_PRICE = 0.01        # Minimum bid on EACH side to consider market "Alive"
LIVE_TRADING = True                # SET TO TRUE FOR REAL ORDER PLACEMENT

# HFT / WebSocket Settings
WS_ENABLED = True
WS_MAX_AGE_SEC = 10                # Max age of WS data before falling back to REST
POLL_INTERVAL_WS = 0.1             # Fast 10hz loop for WebSocket cache checking
POLL_INTERVAL_CORR = 10            # Frequency for correlation/logical scanning

# Cross-Platform Settings
MAX_K_MARKETS = 300                # Max active Kalshi markets to fetch
POLL_INTERVAL_CROSS = 60           # Seconds between cross-platform scans
NLP_MATCH_THRESHOLD = 0.82         # Minimum cosine similarity for semantic matching
