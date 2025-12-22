#!/bin/bash
# Professional Arbitrage Suite - Startup Script
# This script ensures all scanner modules and the data collector are running in the background.

cd "$(dirname "$0")"

# Kill existing processes to ensure a clean start
echo "Shutting down existing bot processes..."
pkill -f poly_scanner.py || true
pkill -f cross_scanner.py || true
pkill -f backtest.py || true
pkill -f correlated_scanner.py || true

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting Polymarket Internal Scanner..."
nohup python3 -u poly_scanner.py > poly.log 2>&1 &

echo "Starting Cross-Platform NLP Scanner..."
nohup python3 -u cross_scanner.py > cross.log 2>&1 &

echo "Starting Correlated Pairs & Spread Scanner..."
nohup python3 -u correlated_scanner.py > correlated.log 2>&1 &

echo "Starting Data Collector (Backtesting)..."
nohup python3 -u backtest.py --collect --interval 300 > collector.log 2>&1 &

echo "------------------------------------------------"
echo "Suite started successfully in background."
echo "Use 'tail -f opportunities.log' to monitor hits."
echo "Use 'pgrep -af python' to verify processes."
echo "------------------------------------------------"
