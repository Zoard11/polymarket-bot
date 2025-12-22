import time
import config

class RiskManager:
    """
    Tracks exposure across markets and events to prevent over-concentration.
    In a live bot, this would be backed by a database or persistent state.
    For this professional scanner suite, we use an in-memory session tracker.
    """
    def __init__(self):
        self.market_exposure = {}  # {market_id: usd_amount}
        self.event_exposure = {}   # {event_ticker/slug: usd_amount}
        self.total_trades = 0
        
    def can_add_position(self, event_id, market_id, amount_usd):
        """Check if adding this position exceeds any risk limits."""
        
        # 1. Total concurrent trades limit
        if self.total_trades >= config.MAX_TOTAL_OPEN_TRADES:
            return False, "Max total concurrent trades reached."
            
        # 2. Per-market exposure limit
        current_m_exp = self.market_exposure.get(market_id, 0)
        if current_m_exp + amount_usd > config.MAX_EXPOSURE_PER_MARKET_USD:
            return False, f"Market exposure limit exceeded (${current_m_exp + amount_usd} > ${config.MAX_EXPOSURE_PER_MARKET_USD})"
            
        # 3. Per-event exposure limit (Correlation Risk)
        current_e_exp = self.event_exposure.get(event_id, 0)
        if current_e_exp + amount_usd > config.MAX_EVENT_EXPOSURE_USD:
            return False, f"Event correlation exposure limit exceeded (${current_e_exp + amount_usd} > ${config.MAX_EVENT_EXPOSURE_USD})"
            
        return True, "Success"

    def record_trade(self, event_id, market_id, amount_usd):
        """Record a successful trade in the tracker."""
        self.market_exposure[market_id] = self.market_exposure.get(market_id, 0) + amount_usd
        self.event_exposure[event_id] = self.event_exposure.get(event_id, 0) + amount_usd
        self.total_trades += 1

# Singleton instance for shared usage
risk_manager = RiskManager()
