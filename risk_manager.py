import time
import config

class RiskManager:
    """
    Tracks exposure across markets and events to prevent over-concentration.
    
    WHY THIS IS IMPORTANT:
    ----------------------
    Without a RiskManager, a bot could:
    1. Open more trades than it has capital for, leading to API rejections or unhedged positions.
    2. Over-concentrate in one market or event, creating a large loss if that market moves.
    3. Lose track of open positions, leading to "runaway" betting.
    
    This class acts as a GATEKEEPER before any order is placed.
    """
    def __init__(self, starting_bankroll_usd=None):
        self.market_exposure = {}  # {market_id: usd_amount}
        self.event_exposure = {}   # {event_ticker/slug: usd_amount}
        self.total_trades = 0
        self.total_capital_locked = 0.0
        self.starting_bankroll = starting_bankroll_usd or getattr(config, 'STARTING_BANKROLL_USD', 50.0)
        
    def can_add_position(self, event_id, market_id, amount_usd):
        """Check if adding this position exceeds any risk limits."""
        
        # 1. Total concurrent trades limit
        if self.total_trades >= config.MAX_TOTAL_OPEN_TRADES:
            return False, f"Max concurrent trades ({config.MAX_TOTAL_OPEN_TRADES}) reached."
            
        # 2. Bankroll / Capital Limit (New!)
        if self.total_capital_locked + amount_usd > self.starting_bankroll:
            return False, f"Insufficient capital (${self.total_capital_locked + amount_usd:.2f} > ${self.starting_bankroll:.2f} bankroll)."
            
        # 3. Per-market exposure limit
        current_m_exp = self.market_exposure.get(market_id, 0)
        if current_m_exp + amount_usd > config.MAX_EXPOSURE_PER_MARKET_USD:
            return False, f"Market exposure limit exceeded."
            
        # 4. Per-event exposure limit (Correlation Risk)
        current_e_exp = self.event_exposure.get(event_id, 0)
        if current_e_exp + amount_usd > config.MAX_EVENT_EXPOSURE_USD:
            return False, f"Event correlation limit exceeded."
            
        return True, "OK"

    def record_trade(self, event_id, market_id, amount_usd):
        """Record a successful trade in the tracker."""
        self.market_exposure[market_id] = self.market_exposure.get(market_id, 0) + amount_usd
        self.event_exposure[event_id] = self.event_exposure.get(event_id, 0) + amount_usd
        self.total_trades += 1
        self.total_capital_locked += amount_usd

    def release_trade(self, event_id, market_id, amount_usd):
        """Release capital when a trade is closed or cancelled (for future use)."""
        self.market_exposure[market_id] = max(0, self.market_exposure.get(market_id, 0) - amount_usd)
        self.event_exposure[event_id] = max(0, self.event_exposure.get(event_id, 0) - amount_usd)
        self.total_trades = max(0, self.total_trades - 1)
        self.total_capital_locked = max(0, self.total_capital_locked - amount_usd)

    def get_status(self):
        """Return a summary of current risk state."""
        return {
            "open_trades": self.total_trades,
            "capital_locked": self.total_capital_locked,
            "remaining_capital": self.starting_bankroll - self.total_capital_locked,
        }

# Singleton instance for shared usage
risk_manager = RiskManager()
