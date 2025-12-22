# Polymarket & Kalshi Arbitrage Scanner Bot

A real-time scanner for identifying "Pure Arbitrage" (Polymarket) and "Cross-Platform Arbitrage" (Polymarket vs Kalshi) opportunities.

## 🚀 Overview

This bot monitors high-volume markets on Polymarket and Kalshi to find risk-free profit opportunities:
1. **Dutch Book Arbitrage**: Combined price of YES and NO shares on Polymarket is < $1.00.
2. **Multi-Outcome Arbitrage**: Sum of all outcomes in a categorical market is < $1.00.
3. **Cross-Platform Arbitrage**: Price discrepancy between Polymarket and Kalshi for the same event (e.g. Poly YES + Kalshi NO < $1.00).

### How it works
1. **Fetch Markets**: Retrieves the top active markets sorted by 24h volume.
2. **Filter**: Focuses on markets with sufficient liquidity and volume.
3. **Order Book Scan**: Fetches real **Ask prices** and checks available **Size** (min $100).
4. **Arbitrage Calculation**: If `Sum(Asks) < $0.99`, it signals a profit opportunity.

## 💻 Usage

### Local Setup
1. **Clone the repo**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run the scanner**:
   - **Single Scan (Test Mode)**: `python scanner.py --once`
   - **Continuous Mode**: `python scanner.py`

### Configuration
Adjust constants in `scanner.py`:
- `MIN_PROFIT_PCT`: Margin threshold (default 1.0%).
- `MIN_VOLUME_24H`: Daily volume floor (default $10,000).
- `MIN_LIQUIDITY_USD`: Min dollar value required at the best price.

---

## ☁️ Oracle Cloud VM Deployment (92.5.20.42)

### 1. Connect via SSH
Ensure your private key is in the local `./ssh` directory.
```bash
ssh -i ./ssh/[your_key] opc@92.5.20.42
```

### 2. Copy Files to the VM
Run from your **local machine**:
```bash
scp -i ./ssh/[your_key] -r ./* opc@92.5.20.42:~/polymarket-bot/
```

### 3. Setup & Run on VM
```bash
cd ~/polymarket-bot/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 scanner.py
```

### 4. Run in Background
Keep the bot alive after closing SSH:
```bash
nohup python3 scanner.py > bot.log 2>&1 &
```
*View logs:* `tail -f bot.log`

---

## ⚠️ Disclaimer
This bot is a **scanner only**. It identifies opportunities but does not execute trades. Use at your own risk.