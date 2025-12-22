# Professional Prediction Market Arbitrage Suite 🦅

Advanced bots for finding and verifying risk-free profit opportunities on Polymarket and Kalshi.

## 🚀 Key Features
- **Professional-Grade Pricing**: Uses **VWAP (Volume Weighted Average Price)** from order book depth rather than just best asks.
- **Realistic Profitability**: Accounts for variable platform fees and estimated slippage.
- **Dynamic Risk Management**: Adjusts profit thresholds based on market volatility (volume).
- **Advanced NLP Matching**: Automatically pairs Polymarket and Kalshi events using `SentenceTransformers` (all-MiniLM-L6-v2).
- **Resilient Execution**: Full API retry logic with exponential backoff and rate-limit handling.
- **Backtesting & Data Archive**: Built-in engine to collect live market snapshots and replay strategies.

---

## 📂 Bot Modules

### 1. Pure Polymarket Scanner (`poly_scanner.py`)
- Fast polling (15s) for internal arbs (Binary & Multi-outcome).
- Optimized for speed as it has no NLP overhead.

### 2. Cross-Platform NLP Scanner (`cross_scanner.py`)
- Finds discrepancies between Poly and Kalshi.
- Semantic matching with 0.82+ confidence requirement.

### 3. Backtesting & Archive (`backtest.py`)
- **Collect**: `python backtest.py --collect` (Archives snapshots to `market_archive.jsonl`).
- **Analyze**: `python backtest.py --analyze market_archive.jsonl` (Replays logic on data).

---

## 🛠️ Configuration (`config.py`)
Modify this file to adjust your risk profile:
- `TARGET_TRADE_SIZE_USD`: The amount you intend to bet (crucial for slippage calculation).
- `FEE_PCT`: Your total combined fee buffer (e.g., 0.5% - 1.0%).
- `MIN_PROFIT_PCT`: Minimum net profit required after all adjustments.

---

## ☁️ Deployment on VM (92.5.20.42)

```bash
# Start the suite in the background
nohup ./venv/bin/python3 -u poly_scanner.py > poly.log 2>&1 &
nohup ./venv/bin/python3 -u cross_scanner.py > cross.log 2>&1 &

# (Optional) Start the data collector for backtesting
nohup ./venv/bin/python3 -u backtest.py --collect > collector.log 2>&1 &
```

### 📊 Monitoring Results
1.  **Scan Logic**: `tail -f poly.log` / `tail -f cross.log`
2.  **Verified Hits**: `tail -f opportunities.log` (Clean list of all identified arbs)