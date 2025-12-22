# Arbitrage Scanner Bot Suite 🦅

Two separate bots for finding risk-free profit opportunities on prediction markets.

## 1. Pure Polymarket Scanner (`poly_scanner.py`)
Focuses exclusively on arbitrage opportunities **within** Polymarket.
- **Binary Dutch Book**: `YES Ask + NO Ask < $1.00`.
- **Multi-Outcome**: `Sum(All Outcome YES Asks) < $1.00`.
- **Speed**: Optimized for fast polling (no NLP overhead).

**How to run:**
```bash
# Local
python poly_scanner.py

# Local (Single check)
python poly_scanner.py --once
```

---

## 2. Cross-Platform NLP Scanner (`cross_scanner.py`)
The advanced version that finds price discrepancies **between** Polymarket and Kalshi.
- **NLP Matching**: Uses `SentenceTransformers` to match questions across sites automatically (No manual mapping needed!).
- **Inter-site Profit**: Checks `Poly(YES) + Kalshi(NO)` and vice-versa.
- **Logic**: Intelligent semantic comparison with a high confidence threshold (0.82+).

**How to run:**
```bash
# Local (Requires sentence-transformers and torch)
python cross_scanner.py
```

---

## ☁️ Oracle Cloud VM Deployment (92.5.20.42)

### 1. Update/Deploy via Git
```bash
# On your local machine
git add .
git commit -m "Separate projects: Pure Poly and Cross NLP"
git push

# On the VM
ssh -i ./ssh/ssh-key-2025-12-22.key opc@92.5.20.42
cd ~/polymarket-bot && git pull
```

### 2. Run Both Bots in Background
You can run both simultaneously using these commands on the VM:
```bash
# Start Polymarket-only bot
nohup ./venv/bin/python3 -u poly_scanner.py > poly.log 2>&1 &

# Start Cross-platform NLP bot
nohup ./venv/bin/python3 -u cross_scanner.py > cross.log 2>&1 &
```

### 3. Monitoring
Check progress in real-time:
*   `tail -f poly.log` (Internal arbs)
*   `tail -f cross.log` (Cross-platform arbs)

---

## ⚠️ Requirements
- `requests`, `python-dotenv` (Both)
- `sentence-transformers`, `torch` (Cross-scanner only)