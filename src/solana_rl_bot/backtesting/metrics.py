"""
Performance Metrics für Backtesting.

Berechnet Trading Performance Metriken:
- Returns (Total, Annualized, CAGR)
- Risk Metrics (Volatility, Sharpe, Sortino, Max Drawdown)
- Trading Metrics (Win Rate, Profit Factor, Trades)
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class PerformanceMetrics:
    """
    Berechnet Performance Metriken für Trading Backtests.
    """

    def __init__(self, risk_free_rate: float = 0.0):
        """
        Initialisiere Performance Metrics.

        Args:
            risk_free_rate: Risk-free Rate (annualisiert, z.B. 0.02 für 2%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_all_metrics(
        self,
        portfolio_values: List[float],
        trades: List[Dict],
        initial_balance: float,
        timestamps: Optional[List[datetime]] = None,
    ) -> Dict:
        """
        Berechne alle Performance Metriken.

        Args:
            portfolio_values: Liste von Portfolio Values
            trades: Liste von Trades
            initial_balance: Initiales Kapital
            timestamps: Optional - Liste von Timestamps

        Returns:
            Dictionary mit allen Metriken
        """
        if len(portfolio_values) == 0:
            return {"error": "Keine Portfolio Values"}

        metrics = {}

        # 1. Return Metrics
        metrics.update(self._calculate_return_metrics(portfolio_values, initial_balance, timestamps))

        # 2. Risk Metrics
        metrics.update(self._calculate_risk_metrics(portfolio_values, initial_balance, timestamps))

        # 3. Trading Metrics
        metrics.update(self._calculate_trading_metrics(trades))

        # 4. Drawdown Metrics
        metrics.update(self._calculate_drawdown_metrics(portfolio_values))

        return metrics

    def _calculate_return_metrics(
        self, portfolio_values: List[float], initial_balance: float, timestamps: Optional[List[datetime]] = None
    ) -> Dict:
        """Berechne Return Metriken."""
        final_value = portfolio_values[-1]
        total_return = (final_value - initial_balance) / initial_balance

        metrics = {
            "initial_balance": initial_balance,
            "final_value": final_value,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "total_profit": final_value - initial_balance,
        }

        # Annualized Return (wenn Timestamps vorhanden)
        if timestamps and len(timestamps) >= 2:
            duration_days = (timestamps[-1] - timestamps[0]).days
            if duration_days > 0:
                years = duration_days / 365.25
                annualized_return = (1 + total_return) ** (1 / years) - 1
                metrics["annualized_return"] = annualized_return
                metrics["annualized_return_pct"] = annualized_return * 100
                metrics["duration_days"] = duration_days

        return metrics

    def _calculate_risk_metrics(
        self, portfolio_values: List[float], initial_balance: float, timestamps: Optional[List[datetime]] = None
    ) -> Dict:
        """Berechne Risk Metriken."""
        # Returns berechnen
        returns = np.diff(portfolio_values) / portfolio_values[:-1]

        if len(returns) == 0:
            return {}

        # Volatility
        volatility = np.std(returns)
        
        # Annualized Volatility (252 trading days)
        if timestamps and len(timestamps) >= 2:
            # Berechne durchschnittliche Zeit zwischen Steps
            time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            avg_seconds = np.mean(time_diffs)
            steps_per_year = (365.25 * 24 * 3600) / avg_seconds
            annualized_volatility = volatility * np.sqrt(steps_per_year)
        else:
            # Fallback: Assume daily data
            annualized_volatility = volatility * np.sqrt(252)

        metrics = {
            "volatility": volatility,
            "annualized_volatility": annualized_volatility,
        }

        # Sharpe Ratio
        mean_return = np.mean(returns)
        if volatility > 0:
            sharpe_ratio = (mean_return - self.risk_free_rate / 252) / volatility
            # Annualized Sharpe
            sharpe_ratio_annualized = sharpe_ratio * np.sqrt(252)
            metrics["sharpe_ratio"] = sharpe_ratio_annualized
        else:
            metrics["sharpe_ratio"] = 0.0

        # Sortino Ratio (nur Downside)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns)
            if downside_std > 0:
                sortino_ratio = (mean_return - self.risk_free_rate / 252) / downside_std
                sortino_ratio_annualized = sortino_ratio * np.sqrt(252)
                metrics["sortino_ratio"] = sortino_ratio_annualized
            else:
                metrics["sortino_ratio"] = 0.0
        else:
            # Keine negativen Returns = perfekt
            metrics["sortino_ratio"] = float('inf')

        return metrics

    def _calculate_trading_metrics(self, trades: List[Dict]) -> Dict:
        """Berechne Trading Metriken."""
        if len(trades) == 0:
            return {"total_trades": 0, "completed_trades": 0}

        # Filtere SELL trades (completed)
        sell_trades = [t for t in trades if t.get("action") == "SELL"]

        if len(sell_trades) == 0:
            return {"total_trades": len(trades), "completed_trades": 0}

        profits = [t["profit"] for t in sell_trades]
        profit_pcts = [t["profit_pct"] for t in sell_trades]

        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p <= 0]

        metrics = {
            "total_trades": len(trades),
            "completed_trades": len(sell_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(sell_trades) if sell_trades else 0,
            "avg_profit": np.mean(profits),
            "avg_profit_pct": np.mean(profit_pcts) * 100,
            "max_profit": max(profits),
            "max_loss": min(profits),
            "total_profit_from_trades": sum(profits),
        }

        # Profit Factor (Gewinn / Verlust Ratio)
        if len(winning_trades) > 0 and len(losing_trades) > 0:
            total_wins = sum(winning_trades)
            total_losses = abs(sum(losing_trades))
            if total_losses > 0:
                metrics["profit_factor"] = total_wins / total_losses
            else:
                metrics["profit_factor"] = float('inf')
        else:
            metrics["profit_factor"] = 0.0

        # Average Win / Average Loss
        if len(winning_trades) > 0:
            metrics["avg_win"] = np.mean(winning_trades)
        else:
            metrics["avg_win"] = 0.0

        if len(losing_trades) > 0:
            metrics["avg_loss"] = np.mean(losing_trades)
        else:
            metrics["avg_loss"] = 0.0

        return metrics

    def _calculate_drawdown_metrics(self, portfolio_values: List[float]) -> Dict:
        """Berechne Drawdown Metriken."""
        portfolio_array = np.array(portfolio_values)

        # Running Maximum
        running_max = np.maximum.accumulate(portfolio_array)

        # Drawdown
        drawdown = (running_max - portfolio_array) / running_max

        # Max Drawdown
        max_drawdown = np.max(drawdown)

        # Max Drawdown Duration (in Steps)
        in_drawdown = drawdown > 0
        if np.any(in_drawdown):
            # Finde längste Drawdown-Periode
            drawdown_starts = np.where(np.diff(np.concatenate(([0], in_drawdown.astype(int)))) == 1)[0]
            drawdown_ends = np.where(np.diff(np.concatenate((in_drawdown.astype(int), [0]))) == -1)[0]
            
            if len(drawdown_starts) > 0 and len(drawdown_ends) > 0:
                drawdown_durations = drawdown_ends - drawdown_starts
                max_drawdown_duration = np.max(drawdown_durations)
            else:
                max_drawdown_duration = 0
        else:
            max_drawdown_duration = 0

        metrics = {
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown * 100,
            "max_drawdown_duration_steps": int(max_drawdown_duration),
        }

        return metrics

    def calculate_calmar_ratio(self, total_return: float, max_drawdown: float, years: float = 1.0) -> float:
        """
        Berechne Calmar Ratio.

        Calmar = Annualized Return / Max Drawdown

        Args:
            total_return: Total Return
            max_drawdown: Max Drawdown (0-1)
            years: Duration in Jahren

        Returns:
            Calmar Ratio
        """
        if max_drawdown == 0:
            return float('inf')

        annualized_return = (1 + total_return) ** (1 / years) - 1
        calmar = annualized_return / max_drawdown

        return calmar

    def compare_to_buy_and_hold(
        self,
        portfolio_values: List[float],
        prices: List[float],
        initial_balance: float,
    ) -> Dict:
        """
        Vergleiche Strategie mit Buy-and-Hold.

        Args:
            portfolio_values: Portfolio Values der Strategie
            prices: Preise (Close) für Buy-and-Hold
            initial_balance: Initiales Kapital

        Returns:
            Dictionary mit Vergleichs-Metriken
        """
        if len(prices) < 2:
            return {}

        # Buy-and-Hold Return
        initial_price = prices[0]
        final_price = prices[-1]
        bah_return = (final_price - initial_price) / initial_price
        bah_final_value = initial_balance * (1 + bah_return)

        # Strategie Return
        strategy_final_value = portfolio_values[-1]
        strategy_return = (strategy_final_value - initial_balance) / initial_balance

        # Alpha (Excess Return)
        alpha = strategy_return - bah_return

        return {
            "buy_and_hold_return": bah_return,
            "buy_and_hold_return_pct": bah_return * 100,
            "buy_and_hold_final_value": bah_final_value,
            "strategy_return": strategy_return,
            "strategy_return_pct": strategy_return * 100,
            "strategy_final_value": strategy_final_value,
            "alpha": alpha,
            "alpha_pct": alpha * 100,
            "outperformance": strategy_return > bah_return,
        }

    def format_metrics(self, metrics: Dict) -> str:
        """
        Formatiere Metriken als lesbaren String.

        Args:
            metrics: Dictionary mit Metriken

        Returns:
            Formatierter String
        """
        lines = []
        lines.append("=" * 60)
        lines.append("PERFORMANCE METRICS")
        lines.append("=" * 60)

        # Return Metrics
        if "total_return" in metrics:
            lines.append("\n[RETURNS]")
            lines.append(f"  Initial Balance:    ${metrics.get('initial_balance', 0):.2f}")
            lines.append(f"  Final Value:        ${metrics.get('final_value', 0):.2f}")
            lines.append(f"  Total Return:       {metrics.get('total_return_pct', 0):+.2f}%")
            if "annualized_return" in metrics:
                lines.append(f"  Annualized Return:  {metrics.get('annualized_return_pct', 0):+.2f}%")

        # Risk Metrics
        if "sharpe_ratio" in metrics:
            lines.append("\n[RISK METRICS]")
            lines.append(f"  Volatility (Ann.):  {metrics.get('annualized_volatility', 0)*100:.2f}%")
            lines.append(f"  Sharpe Ratio:       {metrics.get('sharpe_ratio', 0):.3f}")
            lines.append(f"  Sortino Ratio:      {metrics.get('sortino_ratio', 0):.3f}")
            lines.append(f"  Max Drawdown:       {metrics.get('max_drawdown_pct', 0):.2f}%")

        # Trading Metrics
        if "total_trades" in metrics:
            lines.append("\n[TRADING]")
            lines.append(f"  Total Trades:       {metrics.get('total_trades', 0)}")
            lines.append(f"  Completed Trades:   {metrics.get('completed_trades', 0)}")
            lines.append(f"  Win Rate:           {metrics.get('win_rate', 0)*100:.1f}%")
            lines.append(f"  Profit Factor:      {metrics.get('profit_factor', 0):.2f}")
            lines.append(f"  Avg Profit:         ${metrics.get('avg_profit', 0):.2f}")

        lines.append("=" * 60)

        return "\n".join(lines)
