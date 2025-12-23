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

## ☁️ Deployment on VM (130.61.103.179)

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

### 🔍 Monitoring & Logging
The bot is optimized for high-frequency scanning (10Hz). Use these commands to monitor performance on your VM:

#### 1. Real-Time Activity (See everything)
```bash
tail -f ~/polymarket-bot/maker_gen.log
```

#### 2. Filter for Real Trades (Live Only)
Search the logs for successful order submissions:
```bash
grep -E "Submitted|SUCCESS|Hedge complete" ~/polymarket-bot/maker_gen.log
```

#### 3. Track Profit Opportunities
See all spreads found, regardless of whether a trade was placed:
```bash
tail -f ~/polymarket-bot/opportunities.log
```

#### 4. Debugging & Errors
Check if the bot is hitting rate limits or connection issues:
```bash
grep -i "error\|warn\|fail" ~/polymarket-bot/maker_gen.log
```

#### 5. Verify Bot is Running
```bash
pgrep -af python
```

### 📊 Performance Summary
After a run, you can analyze your `opportunities.log` to see theoretical performance:
```bash
python3 analyze_logs.py

### Handling VM IP Address Changes

When the VM's IP address changes, you may encounter SSH host key verification failures. Follow these steps to resolve:

1. Remove the old host key:
   ```bash
   ssh-keygen -R <old_ip>
   ```

2. Add the new host key:
   ```bash
   ssh-keyscan <new_ip> >> ~/.ssh/known_hosts
   ```

3. Alternatively, connect with automatic acceptance:
   ```bash
   ssh -o StrictHostKeyChecking=accept-new -i <key_path> <user>@<new_ip>
   ```
```