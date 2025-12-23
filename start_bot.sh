#!/bin/bash

# Polymarket Arbitrage Bot Suite - Professional Startup Script
# Targeted for Ubuntu/Linux VPS

echo "--------------------------------------------------"
echo "🚀 Starting Polymarket Arbitrage Bot Suite 🚀"
echo "--------------------------------------------------"

# Kill existing bot processes
pkill -f "scanner.py|backtest.py"

# Auto-Update (User Requested Compatibility)
echo "🔄 Checking for updates..."
git pull origin main

# Install dependencies (using venv python directly, no activation needed)
echo "📦 Installing dependencies..."
./venv/bin/pip install -q -r requirements.txt

# Standard Arbitrage Scanners (DISABLED - No Trading Integration)
# echo "[1/5] Launching Poly Internal Scanner..."
# nohup ./venv/bin/python3 -u poly_scanner.py > poly.log 2>&1 &

# echo "[2/5] Launching Cross-Platform Scanner..."
# nohup ./venv/bin/python3 -u cross_scanner.py > cross.log 2>&1 &

# echo "[3/5] Launching Correlated Pairs Scanner..."
# nohup ./venv/bin/python3 -u correlated_scanner.py > correlated.log 2>&1 &

# Maker / Spread Scanner (HF) - DISABLED (No Trading Integration)
# echo "[5/7] Launching Maker Strategy Scanner (HF)..."
# nohup ./venv/bin/python3 -u maker_scanner.py > maker_hf.log 2>&1 &

# Maker / Spread Scanner (General) - TRADING ENABLED
echo "[1/1] Launching Maker Strategy Scanner (General) with Trading..."
nohup ./venv/bin/python3 -u maker_scanner_general.py > maker_gen.log 2>&1 &

# Data Collector for Backtesting - DISABLED (Not needed for live trading)
# echo "[7/7] Launching Backtest Data Collector..."
# nohup ./venv/bin/python3 -u backtest.py --collect --interval 300 > backtest_collector.log 2>&1 &

echo "--------------------------------------------------"
echo "✅ Trading bot is running in the background."
echo "Use 'pgrep -af python' to verify processes."
echo "Use 'tail -f maker_gen.log' to monitor."
echo "--------------------------------------------------"
