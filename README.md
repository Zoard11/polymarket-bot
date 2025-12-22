# Polymarket Arbitrage Scanner Bot

A real-time scanner for identifying "Pure Arbitrage" opportunities on Polymarket using the Gamma API.

## 🚀 Overview

This bot monitors high-volume binary markets on Polymarket to find "Dutch Book" opportunities where the combined price of **YES** and **NO** shares is less than $1.00. 

### How it works
1. **Fetch Markets**: Retrieves the top 1000 active markets sorted by 24h volume.
2. **Filter**: Focuses on high-volume markets (default >$50k) to ensure liquidity.
3. **Order Book Scan**: For each market, it fetches the actual Order Book **Ask prices**.
4. **Arbitrage Calculation**: If `Price(YES Ask) + Price(NO Ask) < $0.99` (adjustable), it signals an opportunity.

## 🛠 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Zoard11/polymarket-bot.git
   cd polymarket-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage

Run the scanner locally:
```bash
python scanner.py
```

### Configuration
You can adjust the following variables at the top of `scanner.py`:
- `MIN_PROFIT_PCT`: The minimum profit margin (default 1.0%).
- `MIN_VOLUME_24H`: Minimum daily volume to consider a market (default $50,000).
- `POLL_INTERVAL`: How often to repeat the scan (default 10 seconds).

## ⚠️ Disclaimer

This bot is a **scanner only**. It identifies opportunities but does not execute trades. Prediction market arbitrage is highly competitive; significant capital and low-latency infrastructure (VPS) are typically required for successful execution.
