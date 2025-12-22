# Strategy Gap Analysis: Current Bot vs. Professional Benchmarks

This document compares the current functionality of the Arbitrage Suite with the professional strategies used by top Polymarket traders.

## Summary Table

| Strategy | Status | Implementation Details | Missing / Future Work |
| :--- | :--- | :--- | :--- |
| **1. Internal Arbitrage** | ✅ **COMPLETE** | `poly_scanner.py` monitors YES+NO sums. | Dynamic execution via CLOB API (currently monitors/alerts). |
| **2. Statistical Arb** | 🏗️ **PARTIAL** | `correlated_scanner.py` groups by slug/question. | Spread Z-score calculation, long/short convergence logic. |
| **3. AI Prob. Models** | ❌ **MISSING** | NLP used for matching, but not for odds estimation. | Integration with news APIs/X (Twitter) and IV modeling. |
| **4. Spread Farming** | 🏗️ **PARTIAL** | WS Client & CLOB integration implemented. | Active Market-Making (Bid/Ask loop) and Cross-Exchange hedging. |
| **5. Copy-Trading** | ❌ **MISSING** | No wallet/profile scanning logic. | Mirror trading engine, whale track list. |

---

## Detailed Breakdown

### 1. Arbitrage Bots (The "Baguette" Method)
*   **What Works**: Our `poly_scanner.py` polls for YES + NO < $1. We have integrated VWAP and fees to ensure a "True" profit calculation.
*   **Missing**: Automated execution. The bot identifies opportunities but doesn't yet place orders on the CLOB automatically.

### 2. Statistical Arbitrage (The "Sharky" Method)
*   **What Works**: `correlated_scanner.py` identifies related markets.
*   **Missing**: Numerical thresholding (e.g., "7% spread"). We need historical price drift analysis to detect when a correlated pair is "too far apart" to be rational.

### 3. AI Probability Models (The "Circle" Method)
*   **What Works**: We have the infrastructure for `sentence-transformers`.
*   **Missing**: The actual Predictive Model. This requires training a regressor or using LLMs to evaluate news sentiment vs. Polymarket prices.

### 4. Spread Farming (The "Cry" Method)
*   **What Works**: We have Sub-second Polymarket WebSockets (`ws_client.py`).
*   **Missing**: The market-maker loop. This involves placing both buy and sell orders simultaneously to capture the spread (Market Making) rather than just taking liquidity (Arbitrage).

### 5. Copy-Trading Automation
*   **What Works**: API foundation is ready.
*   **Missing**: Tracking logic. We need to fetch the "Leaderboard" or "Profile" data and map transaction history to actions.

---

## Next Recommended Phases
1.  **Phase 5 (Automation)**: Convert alerts to CLOB execution (Strategy 1).
2.  **Phase 6 (Statistical Drift)**: Implement Z-score monitoring for pairs (Strategy 2).
3.  **Phase 7 (Predictive AI)**: Real odds estimation from external data (Strategy 3).
4.  **Phase 8 (Mirror Engine)**: Whale tracking and copy-trading (Strategy 5).
