# Professional Prediction Market Arbitrage Suite 🦅

Advanced bots for finding and verifying risk-free profit opportunities on Polymarket and Kalshi.

## 🚀 Key Features
- **Kelly Criterion Sizing**: Dynamic position sizing based on identified edge and bankroll.
- **Risk Correlation Limits**: Global event-level exposure caps via `risk_manager.py`.
- **Professional-Grade Pricing**: Uses **VWAP (Volume Weighted Average Price)** from order book depth.
- **Realistic Profitability**: Accounts for variable platform fees and estimated slippage.
- **Dynamic Risk Management**: Adjusts profit thresholds based on market volatility (volume).
- **Advanced NLP Matching**: Automatically pairs Polymarket and Kalshi events using `SentenceTransformers`.
- **Advanced Backtesting Metrics**: Annualized Sharpe Ratio, Max Drawdown, and Expectancy reporting.

---

## 📂 Bot Modules

### 1. Pure Polymarket Scanner (`poly_scanner.py`)
- Fast polling (15s) for internal arbs (Binary & Multi-outcome).
- Optimized for speed as it has no NLP overhead.

### 2. Cross-Platform NLP Scanner (`cross_scanner.py`)
- Finds discrepancies between Poly and Kalshi.
- Semantic matching with 0.82+ confidence requirement.

### 3. High-Frequency Scanner (`hf_scanner.py`)
- Targeted "Sniper" for 15-minute "Up or Down" markets.
- High-speed polling (0.2s) for instant execution.

### 4. Maker "Spread" Scanner (`maker_scanner.py` & `maker_scanner_general.py`)
- **HF Lane**: Checks "Up/Down" markets every 1s for spreads.
- **General Lane**: Scans top 200 markets every 15s for "lazy" spreads (NFL, Politics).
- Strategy: Identifies when `Best Bid YES + Best Bid NO < 1.00`.

### 5. Backtesting & Archive (`backtest.py`)
- **Collect**: `python3 backtest.py --collect` (Archives snapshots to `market_archive.jsonl`).
- **Analyze**: `python3 backtest.py --analyze market_archive.jsonl` (Replays logic on data).

#### Running the Backtest
To run the backtest using a virtual environment:

1. Create a virtual environment: `python3 -m venv venv`
2. Activate the virtual environment: `source venv/bin/activate`
3. Run the analysis: `python3 backtest.py --analyze market_archive.jsonl`

---

## 🛠️ Configuration (`config.py`)
Modify this file to adjust your risk profile:
- `BANKROLL_USD`: The amount of capital used for sizing calculations.
- `KELLY_FRACTION`: Conservatism multiplier (e.g., 0.2 for 20% Kelly).
- `MAX_EVENT_EXPOSURE_USD`: Global limit for a single event across all platforms.
- `MIN_PROFIT_PCT`: Minimum net profit required after all adjustments.

---

## ☁️ Deployment on VM (92.5.20.42)

### 🔄 Updating to Latest Version
Run these commands to pull changes and restart the bots:
```bash
cd ~/polymarket-bot
git fetch origin
git reset --hard origin/main
chmod +x start_bot.sh
./start_bot.sh
```

One-liner:
````bash
cd ~/polymarket-bot && git fetch origin && git reset --hard origin/main && chmod +x start_bot.sh && ./start_bot.sh
```

### � Viewing Logs
```bash
# Unified Opportunities
tail -f ~/polymarket-bot/opportunities.log

# Specific Logs
tail -f poly.log
tail -f maker_gen.log
```

### 📊 Monitoring Results
1.  **Scan Logic**: `tail -f poly.log` / `tail -f cross.log`
2.  **Verified Hits**: `tail -f opportunities.log` (Clean list of all identified arbs)