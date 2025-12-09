# -*- coding: utf-8 -*-
"""
Risk Manager - Optimiert fuer SOL/USDT Trading.

Basierend auf Analyse der echten SOL-Marktdaten:
- Taegliche Volatilitaet: ~4.7%
- ATR: ~0.35% pro 5min Candle
- Max historischer Drawdown: -67.5%
- Typische Bewegung: 0.13% pro 5min

Diese Parameter sind speziell fuer Solana kalibriert!
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple
import numpy as np


@dataclass
class RiskConfig:
    """
    Risk Management Konfiguration - Optimiert fuer SOL.

    Alle Werte basieren auf historischer SOL/USDT Analyse.
    """

    # === TIMEFRAME INFO ===
    timeframe: str = "5min"                 # Timeframe fuer diese Config

    # === POSITION SIZING ===
    max_position_pct: float = 0.25          # Max 25% pro Trade
    min_position_pct: float = 0.10          # Min 10% pro Trade

    # === STOP-LOSS ===
    stop_loss_pct: float = 0.10             # -10% Stop-Loss

    # === TAKE-PROFIT (2:1 Risk-Reward Ratio) ===
    take_profit_pct: float = 0.20           # +20% Take-Profit

    # === TRAILING STOP ===
    use_trailing_stop: bool = True
    trailing_stop_pct: float = 0.05         # 5% Trailing (nach Profit)
    trailing_activation_pct: float = 0.08   # Aktiviert bei +8% Profit

    # === PORTFOLIO RISK ===
    max_drawdown_pct: float = 0.20          # -20% Max Drawdown -> Stop
    max_daily_loss_pct: float = 0.08        # -8% Max Verlust pro Tag

    # === TRADE LIMITS ===
    max_trades_per_day: int = 15            # Verhindert Overtrading
    min_trade_interval_candles: int = 6     # Min Candles zwischen Trades

    # === VOLATILITAETS-ANPASSUNG ===
    use_volatility_scaling: bool = True
    volatility_lookback: int = 288          # Lookback in Candles
    low_vol_multiplier: float = 1.5         # Groessere Position bei niedriger Vol
    high_vol_multiplier: float = 0.5        # Kleinere Position bei hoher Vol

    # === RISIKO PRO TRADE ===
    max_risk_per_trade_pct: float = 0.02    # Max 2% Kapital-Risiko pro Trade


class RiskConfigFactory:
    """
    Factory fuer timeframe-spezifische Risk Configs.

    Jeder Timeframe hat optimierte Parameter basierend auf:
    - Volatilitaet des Timeframes
    - Typische Haltezeit
    - Trading-Frequenz
    """

    @staticmethod
    def create(timeframe: str) -> RiskConfig:
        """
        Erstelle optimierte RiskConfig fuer Timeframe.

        Args:
            timeframe: "1min", "5min", "15min", "1h", "4h", "1d"

        Returns:
            Optimierte RiskConfig
        """
        configs = {
            # === 1 MINUTE === (Scalping)
            "1min": RiskConfig(
                timeframe="1min",
                # Position: Kleiner wegen hoher Frequenz
                max_position_pct=0.15,
                min_position_pct=0.05,
                # Enger Stop wegen schneller Trades
                stop_loss_pct=0.03,          # -3%
                take_profit_pct=0.05,        # +5%
                # Trailing
                use_trailing_stop=True,
                trailing_stop_pct=0.02,      # 2%
                trailing_activation_pct=0.03, # Nach +3%
                # Portfolio
                max_drawdown_pct=0.15,       # Strenger wegen vieler Trades
                max_daily_loss_pct=0.05,
                # Limits: Viele schnelle Trades
                max_trades_per_day=30,
                min_trade_interval_candles=5, # 5 min zwischen Trades
                # Volatilitaet
                volatility_lookback=60,      # 1h Lookback
            ),

            # === 5 MINUTEN === (Day Trading)
            "5min": RiskConfig(
                timeframe="5min",
                max_position_pct=0.25,
                min_position_pct=0.10,
                stop_loss_pct=0.08,          # -8%
                take_profit_pct=0.15,        # +15%
                use_trailing_stop=True,
                trailing_stop_pct=0.04,      # 4%
                trailing_activation_pct=0.06, # Nach +6%
                max_drawdown_pct=0.20,
                max_daily_loss_pct=0.08,
                max_trades_per_day=15,
                min_trade_interval_candles=6, # 30 min
                volatility_lookback=288,     # 1 Tag
            ),

            # === 15 MINUTEN === (Intraday)
            "15min": RiskConfig(
                timeframe="15min",
                max_position_pct=0.30,
                min_position_pct=0.10,
                stop_loss_pct=0.10,          # -10%
                take_profit_pct=0.20,        # +20%
                use_trailing_stop=True,
                trailing_stop_pct=0.05,      # 5%
                trailing_activation_pct=0.08, # Nach +8%
                max_drawdown_pct=0.20,
                max_daily_loss_pct=0.08,
                max_trades_per_day=10,
                min_trade_interval_candles=4, # 1h
                volatility_lookback=96,      # 1 Tag (96 x 15min)
            ),

            # === 1 STUNDE === (Swing Trading)
            "1h": RiskConfig(
                timeframe="1h",
                max_position_pct=0.35,
                min_position_pct=0.15,
                stop_loss_pct=0.12,          # -12%
                take_profit_pct=0.25,        # +25%
                use_trailing_stop=True,
                trailing_stop_pct=0.06,      # 6%
                trailing_activation_pct=0.10, # Nach +10%
                max_drawdown_pct=0.25,
                max_daily_loss_pct=0.10,
                max_trades_per_day=5,
                min_trade_interval_candles=4, # 4h
                volatility_lookback=24,      # 1 Tag (24 x 1h)
            ),

            # === 4 STUNDEN === (Position Trading)
            "4h": RiskConfig(
                timeframe="4h",
                max_position_pct=0.40,
                min_position_pct=0.20,
                stop_loss_pct=0.15,          # -15%
                take_profit_pct=0.30,        # +30%
                use_trailing_stop=True,
                trailing_stop_pct=0.08,      # 8%
                trailing_activation_pct=0.12, # Nach +12%
                max_drawdown_pct=0.25,
                max_daily_loss_pct=0.12,
                max_trades_per_day=3,
                min_trade_interval_candles=3, # 12h
                volatility_lookback=42,      # 1 Woche (42 x 4h)
            ),

            # === 1 TAG === (Macro Trading)
            "1d": RiskConfig(
                timeframe="1d",
                max_position_pct=0.50,
                min_position_pct=0.25,
                stop_loss_pct=0.20,          # -20%
                take_profit_pct=0.40,        # +40%
                use_trailing_stop=True,
                trailing_stop_pct=0.10,      # 10%
                trailing_activation_pct=0.15, # Nach +15%
                max_drawdown_pct=0.30,
                max_daily_loss_pct=0.15,
                max_trades_per_day=1,
                min_trade_interval_candles=3, # 3 Tage
                volatility_lookback=30,      # 1 Monat
            ),
        }

        if timeframe not in configs:
            raise ValueError(f"Unbekannter Timeframe: {timeframe}. "
                           f"Verfuegbar: {list(configs.keys())}")

        return configs[timeframe]

    @staticmethod
    def get_all_timeframes() -> list:
        """Liste aller verfuegbaren Timeframes."""
        return ["1min", "5min", "15min", "1h", "4h", "1d"]


class RiskManager:
    """
    Risk Manager fuer SOL Trading.

    Handhabt:
    - Position Sizing (dynamisch basierend auf Volatilitaet)
    - Stop-Loss / Take-Profit
    - Trailing Stops
    - Max Drawdown Protection
    - Daily Loss Limits
    - Trade Frequency Limits
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        """Initialisiere Risk Manager."""
        self.config = config or RiskConfig()

        # State
        self.initial_balance: float = 0.0
        self.peak_balance: float = 0.0
        self.daily_start_balance: float = 0.0
        self.current_day: Optional[str] = None
        self.trades_today: int = 0
        self.last_trade_step: int = -999

        # Position State
        self.entry_price: float = 0.0
        self.highest_since_entry: float = 0.0
        self.trailing_stop_active: bool = False

    def reset(self, initial_balance: float):
        """Reset Risk Manager fuer neue Episode."""
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.current_day = None
        self.trades_today = 0
        self.last_trade_step = -999
        self.entry_price = 0.0
        self.highest_since_entry = 0.0
        self.trailing_stop_active = False

    def update_day(self, timestamp, balance: float):
        """Update daily tracking."""
        day = str(timestamp)[:10] if timestamp else None

        if day != self.current_day:
            self.current_day = day
            self.daily_start_balance = balance
            self.trades_today = 0

    def update_peak(self, balance: float):
        """Update peak balance fuer Drawdown Berechnung."""
        if balance > self.peak_balance:
            self.peak_balance = balance

    def get_current_drawdown(self, balance: float) -> float:
        """Berechne aktuellen Drawdown."""
        if self.peak_balance <= 0:
            return 0.0
        return (balance - self.peak_balance) / self.peak_balance

    def get_daily_pnl(self, balance: float) -> float:
        """Berechne heutigen PnL."""
        if self.daily_start_balance <= 0:
            return 0.0
        return (balance - self.daily_start_balance) / self.daily_start_balance

    def calculate_position_size(
        self,
        balance: float,
        current_price: float,
        volatility: Optional[float] = None,
    ) -> float:
        """
        Berechne optimale Position Size.

        Args:
            balance: Aktuelles Kapital
            current_price: Aktueller Preis
            volatility: Aktuelle Volatilitaet (optional)

        Returns:
            Position Size als Anteil des Kapitals (0.0 - max_position_pct)
        """
        base_size = self.config.max_position_pct

        # Volatilitaets-Anpassung
        if self.config.use_volatility_scaling and volatility is not None:
            # Normale Vol fuer SOL: ~4.7% pro Tag
            normal_vol = 0.047

            if volatility < normal_vol * 0.7:  # Niedrige Vol
                base_size *= self.config.low_vol_multiplier
            elif volatility > normal_vol * 1.3:  # Hohe Vol
                base_size *= self.config.high_vol_multiplier

        # Risk-basierte Anpassung
        # Max 2% Risiko pro Trade bei 10% Stop-Loss = max 20% Position
        risk_based_size = self.config.max_risk_per_trade_pct / self.config.stop_loss_pct

        # Nehme das Minimum
        final_size = min(base_size, risk_based_size, self.config.max_position_pct)
        final_size = max(final_size, self.config.min_position_pct)

        return final_size

    def can_open_trade(self, balance: float, current_step: int) -> Tuple[bool, str]:
        """
        Pruefe ob neuer Trade erlaubt ist.

        Returns:
            (allowed, reason)
        """
        # Max Drawdown Check
        drawdown = self.get_current_drawdown(balance)
        if drawdown < -self.config.max_drawdown_pct:
            return False, f"Max Drawdown erreicht ({drawdown*100:.1f}%)"

        # Daily Loss Check
        daily_pnl = self.get_daily_pnl(balance)
        if daily_pnl < -self.config.max_daily_loss_pct:
            return False, f"Max Daily Loss erreicht ({daily_pnl*100:.1f}%)"

        # Trade Frequency Check
        if self.trades_today >= self.config.max_trades_per_day:
            return False, f"Max Trades pro Tag erreicht ({self.trades_today})"

        # Min Interval Check
        steps_since_last = current_step - self.last_trade_step
        if steps_since_last < self.config.min_trade_interval_candles:
            return False, f"Min Trade Interval ({steps_since_last}/{self.config.min_trade_interval_candles})"

        return True, "OK"

    def on_trade_open(self, entry_price: float, current_step: int):
        """Wird aufgerufen wenn Trade geoeffnet wird."""
        self.entry_price = entry_price
        self.highest_since_entry = entry_price
        self.trailing_stop_active = False
        self.trades_today += 1
        self.last_trade_step = current_step

    def on_price_update(self, current_price: float) -> Optional[str]:
        """
        Update bei neuem Preis. Prueft Stop-Loss/Take-Profit.

        Args:
            current_price: Aktueller Preis

        Returns:
            "STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP" oder None
        """
        if self.entry_price <= 0:
            return None

        # Update highest price
        if current_price > self.highest_since_entry:
            self.highest_since_entry = current_price

        # Berechne PnL
        pnl_pct = (current_price - self.entry_price) / self.entry_price

        # Stop-Loss Check
        if pnl_pct <= -self.config.stop_loss_pct:
            return "STOP_LOSS"

        # Take-Profit Check
        if pnl_pct >= self.config.take_profit_pct:
            return "TAKE_PROFIT"

        # Trailing Stop
        if self.config.use_trailing_stop:
            # Aktiviere Trailing Stop bei genug Profit
            if pnl_pct >= self.config.trailing_activation_pct:
                self.trailing_stop_active = True

            if self.trailing_stop_active:
                # Berechne Trailing Stop Level
                trailing_stop_price = self.highest_since_entry * (1 - self.config.trailing_stop_pct)

                if current_price <= trailing_stop_price:
                    return "TRAILING_STOP"

        return None

    def on_trade_close(self):
        """Wird aufgerufen wenn Trade geschlossen wird."""
        self.entry_price = 0.0
        self.highest_since_entry = 0.0
        self.trailing_stop_active = False

    def get_stop_loss_price(self) -> float:
        """Berechne aktuellen Stop-Loss Preis."""
        if self.entry_price <= 0:
            return 0.0

        if self.trailing_stop_active:
            return self.highest_since_entry * (1 - self.config.trailing_stop_pct)
        else:
            return self.entry_price * (1 - self.config.stop_loss_pct)

    def get_take_profit_price(self) -> float:
        """Berechne Take-Profit Preis."""
        if self.entry_price <= 0:
            return 0.0
        return self.entry_price * (1 + self.config.take_profit_pct)

    def get_status(self, balance: float) -> Dict:
        """Hole aktuellen Risk Status."""
        return {
            "drawdown": self.get_current_drawdown(balance),
            "daily_pnl": self.get_daily_pnl(balance),
            "trades_today": self.trades_today,
            "trailing_stop_active": self.trailing_stop_active,
            "stop_loss_price": self.get_stop_loss_price(),
            "take_profit_price": self.get_take_profit_price(),
        }

    def __repr__(self) -> str:
        return (
            f"RiskManager(\n"
            f"  position_size: {self.config.min_position_pct*100:.0f}-{self.config.max_position_pct*100:.0f}%\n"
            f"  stop_loss: -{self.config.stop_loss_pct*100:.0f}%\n"
            f"  take_profit: +{self.config.take_profit_pct*100:.0f}%\n"
            f"  trailing_stop: {self.config.trailing_stop_pct*100:.0f}% (after +{self.config.trailing_activation_pct*100:.0f}%)\n"
            f"  max_drawdown: -{self.config.max_drawdown_pct*100:.0f}%\n"
            f"  max_daily_loss: -{self.config.max_daily_loss_pct*100:.0f}%\n"
            f")"
        )
