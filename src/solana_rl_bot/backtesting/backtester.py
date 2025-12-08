"""
Backtester für RL Trading Agents.

Führt Backtests auf historischen Daten aus und sammelt Performance Metriken.
"""

from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime

from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.backtesting.metrics import PerformanceMetrics
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class Backtester:
    """
    Backtesting Framework für RL Trading Agents.
    """

    def __init__(
        self,
        env: TradingEnv,
        metrics_calculator: Optional[PerformanceMetrics] = None,
    ):
        """
        Initialisiere Backtester.

        Args:
            env: Trading Environment
            metrics_calculator: Optional PerformanceMetrics Instanz
        """
        self.env = env
        self.metrics = metrics_calculator or PerformanceMetrics()

        logger.info("Backtester initialisiert")

    def run_backtest(
        self,
        agent: Callable,
        deterministic: bool = True,
        verbose: bool = False,
    ) -> Dict:
        """
        Führe Backtest aus.

        Args:
            agent: Agent Function (observation -> action)
            deterministic: Deterministisch (no exploration)
            verbose: Verbose logging

        Returns:
            Dictionary mit Backtest-Ergebnissen
        """
        logger.info("Starte Backtest...")

        # Reset Environment
        observation, info = self.env.reset()

        # Tracking
        done = False
        truncated = False
        step_count = 0
        total_reward = 0.0

        portfolio_history = []
        actions_history = []
        prices_history = []
        timestamps_history = []

        while not (done or truncated):
            # Agent Prediction
            action = agent(observation)

            # Environment Step
            observation, reward, done, truncated, info = self.env.step(action)

            # Track
            step_count += 1
            total_reward += reward
            portfolio_history.append(info["portfolio_value"])
            actions_history.append(action)

            # Price und Timestamp
            current_price = self.env.df.iloc[self.env.current_step]["close"]
            prices_history.append(current_price)

            if "timestamp" in self.env.df.columns:
                timestamp = self.env.df.iloc[self.env.current_step]["timestamp"]
                timestamps_history.append(timestamp)

            if verbose and step_count % 50 == 0:
                logger.info(
                    f"Step {step_count}: Portfolio=${info['portfolio_value']:.2f}, "
                    f"Return={info['total_return']*100:+.2f}%"
                )

        # Backtest Stats
        stats = self.env.get_trade_statistics()

        # Performance Metriken
        timestamps = timestamps_history if len(timestamps_history) > 0 else None
        performance = self.metrics.calculate_all_metrics(
            portfolio_values=portfolio_history,
            trades=self.env.trades,
            initial_balance=self.env.initial_balance,
            timestamps=timestamps,
        )

        # Buy-and-Hold Vergleich
        if len(prices_history) >= 2:
            bah_comparison = self.metrics.compare_to_buy_and_hold(
                portfolio_values=portfolio_history,
                prices=prices_history,
                initial_balance=self.env.initial_balance,
            )
            performance.update(bah_comparison)

        # Kombiniere Ergebnisse
        results = {
            "steps": step_count,
            "total_reward": total_reward,
            "portfolio_history": portfolio_history,
            "actions_history": actions_history,
            "prices_history": prices_history,
            "timestamps_history": timestamps_history,
            "trades": self.env.trades,
            "stats": stats,
            "performance": performance,
        }

        logger.info(
            f"✅ Backtest abgeschlossen: {step_count} Steps, "
            f"Return: {performance.get('total_return_pct', 0):+.2f}%"
        )

        return results

    def run_multiple_backtests(
        self,
        agent: Callable,
        n_runs: int = 10,
        deterministic: bool = True,
    ) -> List[Dict]:
        """
        Führe mehrere Backtests aus (mit verschiedenen Seeds).

        Args:
            agent: Agent Function
            n_runs: Anzahl Runs
            deterministic: Deterministisch

        Returns:
            Liste von Backtest-Ergebnissen
        """
        logger.info(f"Starte {n_runs} Backtests...")

        results = []

        for run in range(n_runs):
            logger.info(f"Run {run + 1}/{n_runs}")

            # Backtest
            result = self.run_backtest(agent, deterministic=deterministic, verbose=False)

            results.append(result)

        # Aggregiere Statistiken
        aggregated = self._aggregate_results(results)

        logger.info(
            f"✅ {n_runs} Backtests abgeschlossen. "
            f"Avg Return: {aggregated['avg_return']*100:+.2f}% ± {aggregated['std_return']*100:.2f}%"
        )

        return results

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregiere Ergebnisse von mehreren Backtests."""
        returns = [r["performance"]["total_return"] for r in results]
        sharpes = [r["performance"].get("sharpe_ratio", 0) for r in results]
        max_dds = [r["performance"]["max_drawdown"] for r in results]

        aggregated = {
            "n_runs": len(results),
            "avg_return": np.mean(returns),
            "std_return": np.std(returns),
            "best_return": max(returns),
            "worst_return": min(returns),
            "avg_sharpe": np.mean(sharpes),
            "avg_max_drawdown": np.mean(max_dds),
        }

        return aggregated

    def walk_forward_analysis(
        self,
        df: pd.DataFrame,
        agent: Callable,
        train_size: int = 1000,
        test_size: int = 200,
        step_size: int = 100,
    ) -> List[Dict]:
        """
        Walk-Forward Analysis.

        Teilt Daten in überlappende Train/Test Windows.

        Args:
            df: Komplettes DataFrame
            agent: Agent Function
            train_size: Training Window Size
            test_size: Test Window Size
            step_size: Schritt-Größe

        Returns:
            Liste von Test-Ergebnissen
        """
        logger.info(
            f"Starte Walk-Forward Analysis: "
            f"Train={train_size}, Test={test_size}, Step={step_size}"
        )

        results = []
        start_idx = 0

        while start_idx + train_size + test_size <= len(df):
            # Train Window
            train_start = start_idx
            train_end = start_idx + train_size

            # Test Window
            test_start = train_end
            test_end = test_start + test_size

            logger.info(
                f"Window: Train[{train_start}:{train_end}], Test[{test_start}:{test_end}]"
            )

            # Test auf Test Window
            test_df = df.iloc[test_start:test_end].copy()

            # Erstelle neues Environment für Test
            test_env = TradingEnv(
                df=test_df,
                initial_balance=self.env.initial_balance,
                commission=self.env.commission,
                reward_type=self.env.reward_function.name,
            )

            # Temporärer Backtester
            temp_backtester = Backtester(test_env, self.metrics)

            # Backtest
            result = temp_backtester.run_backtest(agent, deterministic=True, verbose=False)

            result["window"] = {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
            }

            results.append(result)

            # Nächstes Window
            start_idx += step_size

        # Aggregiere Walk-Forward Results
        if len(results) > 0:
            wf_stats = self._aggregate_walk_forward_results(results)
            logger.info(
                f"✅ Walk-Forward Analysis abgeschlossen: {len(results)} Windows, "
                f"Avg Return: {wf_stats['avg_return']*100:+.2f}%"
            )

        return results

    def _aggregate_walk_forward_results(self, results: List[Dict]) -> Dict:
        """Aggregiere Walk-Forward Results."""
        returns = [r["performance"]["total_return"] for r in results]
        sharpes = [r["performance"].get("sharpe_ratio", 0) for r in results]

        return {
            "n_windows": len(results),
            "avg_return": np.mean(returns),
            "std_return": np.std(returns),
            "best_return": max(returns),
            "worst_return": min(returns),
            "avg_sharpe": np.mean(sharpes),
            "win_rate": sum(1 for r in returns if r > 0) / len(returns),
        }

    def benchmark_against_random(self, n_runs: int = 10) -> Dict:
        """
        Benchmark gegen Random Agent.

        Args:
            n_runs: Anzahl Random Runs

        Returns:
            Benchmark-Ergebnisse
        """
        logger.info(f"Benchmark gegen Random Agent ({n_runs} runs)...")

        def random_agent(observation):
            return self.env.action_space.sample()

        # Multiple Runs
        random_results = self.run_multiple_backtests(random_agent, n_runs=n_runs)

        # Aggregiere
        random_stats = self._aggregate_results(random_results)

        logger.info(
            f"Random Agent Baseline: Return={random_stats['avg_return']*100:+.2f}% ± "
            f"{random_stats['std_return']*100:.2f}%"
        )

        return {
            "random_agent_stats": random_stats,
            "random_results": random_results,
        }
