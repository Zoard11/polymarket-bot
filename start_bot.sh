#!/bin/bash

# Polymarket Arbitrage Bot Suite - Professional Startup Script
# Targeted for Ubuntu/Linux VPS

echo "--------------------------------------------------"
echo "🚀 Starting Polymarket Arbitrage Bot Suite 🚀"
echo "--------------------------------------------------"

# Kill existing python processes to avoid duplicates
pkill -f python3

# Standard Arbitrage Scanners
echo "[1/5] Launching Poly Internal Scanner..."
nohup python3 -u poly_scanner.py > poly.log 2>&1 &

echo "[2/5] Launching Cross-Platform Scanner..."
nohup python3 -u cross_scanner.py > cross.log 2>&1 &

echo "[3/5] Launching Correlated Pairs Scanner..."
nohup python3 -u correlated_scanner.py > correlated.log 2>&1 &

# High-Frequency (15-min) Scanner
echo "[4/5] Launching 15-Min HF Scanner..."
nohup python3 -u hf_scanner.py > hf.log 2>&1 &

# Data Collector for Backtesting
echo "[5/5] Launching Backtest Data Collector..."
nohup python3 -u backtest.py --collect --interval 300 > backtest_collector.log 2>&1 &

echo "--------------------------------------------------"
echo "✅ All bots are running in the background."
echo "Use 'pgrep -af python' to verify processes."
echo "Use 'tail -f <log_name>.log' to monitor."
echo "--------------------------------------------------"
