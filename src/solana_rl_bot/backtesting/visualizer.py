"""
Visualizer für Backtest-Ergebnisse.

Erstellt Plots und Tabellen für Performance-Analyse.
"""

from typing import Dict, List, Optional
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)
console = Console()


class BacktestVisualizer:
    """
    Visualizer für Backtest-Ergebnisse.
    """

    def __init__(self):
        """Initialisiere Visualizer."""
        pass

    def print_results(self, results: Dict, title: str = "Backtest Results"):
        """
        Drucke Backtest-Ergebnisse in schönem Format.

        Args:
            results: Backtest-Ergebnisse Dictionary
            title: Titel für Output
        """
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
        console.print("=" * 60)

        # Performance Metrics
        perf = results.get("performance", {})

        # Return Metrics
        console.print("\n[yellow]RETURNS[/yellow]")
        console.print(f"  Initial Balance:    ${perf.get('initial_balance', 0):.2f}")
        console.print(f"  Final Value:        ${perf.get('final_value', 0):.2f}")
        console.print(f"  Total Return:       {perf.get('total_return_pct', 0):+.2f}%")
        if "annualized_return_pct" in perf:
            console.print(f"  Annualized Return:  {perf.get('annualized_return_pct', 0):+.2f}%")

        # Risk Metrics
        if "sharpe_ratio" in perf:
            console.print("\n[yellow]RISK METRICS[/yellow]")
            console.print(f"  Volatility (Ann.):  {perf.get('annualized_volatility', 0)*100:.2f}%")
            console.print(f"  Sharpe Ratio:       {perf.get('sharpe_ratio', 0):.3f}")
            console.print(f"  Sortino Ratio:      {perf.get('sortino_ratio', 0):.3f}")
            console.print(f"  Max Drawdown:       {perf.get('max_drawdown_pct', 0):.2f}%")

        # Trading Metrics
        if "total_trades" in perf:
            console.print("\n[yellow]TRADING[/yellow]")
            console.print(f"  Total Trades:       {perf.get('total_trades', 0)}")
            console.print(f"  Completed Trades:   {perf.get('completed_trades', 0)}")
            console.print(f"  Win Rate:           {perf.get('win_rate', 0)*100:.1f}%")
            console.print(f"  Profit Factor:      {perf.get('profit_factor', 0):.2f}")
            console.print(f"  Avg Profit:         ${perf.get('avg_profit', 0):.2f}")

        # Buy-and-Hold Comparison
        if "buy_and_hold_return" in perf:
            console.print("\n[yellow]VS BUY-AND-HOLD[/yellow]")
            console.print(f"  B&H Return:         {perf.get('buy_and_hold_return_pct', 0):+.2f}%")
            console.print(f"  Strategy Return:    {perf.get('strategy_return_pct', 0):+.2f}%")
            console.print(f"  Alpha:              {perf.get('alpha_pct', 0):+.2f}%")
            
            outperformance = perf.get('outperformance', False)
            status = "[green]✅ Outperform[/green]" if outperformance else "[red]❌ Underperform[/red]"
            console.print(f"  Status:             {status}")

        console.print("=" * 60)

    def print_comparison_table(self, results_list: List[Dict], labels: List[str]):
        """
        Drucke Vergleichs-Tabelle für mehrere Backtest-Ergebnisse.

        Args:
            results_list: Liste von Backtest-Ergebnissen
            labels: Labels für jedes Result
        """
        table = Table(title="Backtest Comparison")

        table.add_column("Metric", style="cyan")
        for label in labels:
            table.add_column(label, style="yellow")

        # Metrics to compare
        metrics = [
            ("Total Return", "total_return_pct", "%"),
            ("Sharpe Ratio", "sharpe_ratio", ""),
            ("Max Drawdown", "max_drawdown_pct", "%"),
            ("Win Rate", "win_rate", "%"),
            ("Trades", "completed_trades", ""),
            ("Profit Factor", "profit_factor", ""),
        ]

        for metric_name, metric_key, suffix in metrics:
            row = [metric_name]
            
            for results in results_list:
                perf = results.get("performance", {})
                value = perf.get(metric_key, 0)
                
                if metric_key == "win_rate":
                    value *= 100  # Convert to percentage
                
                if suffix == "%":
                    formatted = f"{value:+.2f}%"
                elif suffix == "":
                    formatted = f"{value:.2f}"
                else:
                    formatted = f"{value:.2f}{suffix}"
                
                row.append(formatted)
            
            table.add_row(*row)

        console.print(table)

    def print_walk_forward_results(self, wf_results: List[Dict]):
        """
        Drucke Walk-Forward Analysis Ergebnisse.

        Args:
            wf_results: Liste von Walk-Forward Test-Ergebnissen
        """
        console.print("\n[bold cyan]Walk-Forward Analysis Results[/bold cyan]")
        console.print("=" * 60)

        table = Table(title="Walk-Forward Windows")
        table.add_column("Window", style="cyan")
        table.add_column("Test Period", style="yellow")
        table.add_column("Return", style="green")
        table.add_column("Sharpe", style="magenta")
        table.add_column("Max DD", style="red")
        table.add_column("Trades", style="blue")

        for i, result in enumerate(wf_results):
            window_info = result.get("window", {})
            perf = result.get("performance", {})

            test_range = f"[{window_info['test_start']}:{window_info['test_end']}]"
            
            table.add_row(
                f"#{i+1}",
                test_range,
                f"{perf.get('total_return_pct', 0):+.2f}%",
                f"{perf.get('sharpe_ratio', 0):.2f}",
                f"{perf.get('max_drawdown_pct', 0):.2f}%",
                str(perf.get('completed_trades', 0)),
            )

        console.print(table)

        # Aggregierte Stats
        returns = [r["performance"]["total_return"] for r in wf_results]
        sharpes = [r["performance"].get("sharpe_ratio", 0) for r in wf_results]

        console.print(f"\n[yellow]Aggregated Statistics[/yellow]")
        console.print(f"  Windows:            {len(wf_results)}")
        console.print(f"  Avg Return:         {np.mean(returns)*100:+.2f}% ± {np.std(returns)*100:.2f}%")
        console.print(f"  Best Return:        {max(returns)*100:+.2f}%")
        console.print(f"  Worst Return:       {min(returns)*100:+.2f}%")
        console.print(f"  Avg Sharpe:         {np.mean(sharpes):.3f}")
        console.print(f"  Win Rate (>0):      {sum(1 for r in returns if r > 0) / len(returns) * 100:.1f}%")

    def print_summary_panel(self, results: Dict):
        """
        Drucke kompakte Summary in Panel.

        Args:
            results: Backtest-Ergebnisse
        """
        perf = results.get("performance", {})

        summary_text = f"""
[bold]Return:[/bold] {perf.get('total_return_pct', 0):+.2f}%
[bold]Sharpe:[/bold] {perf.get('sharpe_ratio', 0):.3f}
[bold]Max DD:[/bold] {perf.get('max_drawdown_pct', 0):.2f}%
[bold]Win Rate:[/bold] {perf.get('win_rate', 0)*100:.1f}%
[bold]Trades:[/bold] {perf.get('completed_trades', 0)}
"""

        panel = Panel(
            summary_text.strip(),
            title="[bold cyan]Backtest Summary[/bold cyan]",
            border_style="cyan",
        )

        console.print(panel)

    def print_trade_log(self, trades: List[Dict], limit: int = 10):
        """
        Drucke Trade Log.

        Args:
            trades: Liste von Trades
            limit: Max Anzahl zu zeigen
        """
        console.print(f"\n[bold cyan]Trade Log (Last {limit})[/bold cyan]")

        table = Table()
        table.add_column("Step", style="cyan")
        table.add_column("Action", style="yellow")
        table.add_column("Price", style="green")
        table.add_column("Profit", style="magenta")
        table.add_column("Profit %", style="blue")

        # Zeige letzte N trades
        recent_trades = trades[-limit:] if len(trades) > limit else trades

        for trade in recent_trades:
            action = trade.get("action", "")
            
            if action == "BUY":
                table.add_row(
                    str(trade.get("step", 0)),
                    "BUY",
                    f"${trade.get('price', 0):.2f}",
                    "-",
                    "-",
                )
            elif action == "SELL":
                profit = trade.get("profit", 0)
                profit_pct = trade.get("profit_pct", 0) * 100
                
                profit_str = f"${profit:+.2f}"
                profit_pct_str = f"{profit_pct:+.2f}%"
                
                # Color based on profit/loss
                if profit > 0:
                    profit_str = f"[green]{profit_str}[/green]"
                    profit_pct_str = f"[green]{profit_pct_str}[/green]"
                else:
                    profit_str = f"[red]{profit_str}[/red]"
                    profit_pct_str = f"[red]{profit_pct_str}[/red]"
                
                table.add_row(
                    str(trade.get("step", 0)),
                    "SELL",
                    f"${trade.get('price', 0):.2f}",
                    profit_str,
                    profit_pct_str,
                )

        console.print(table)
