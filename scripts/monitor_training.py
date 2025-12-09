#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Training Progress Monitor

Zeigt den aktuellen Fortschritt des laufenden Trainings an.
"""

import sys
from pathlib import Path
import time
import re
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def parse_log_file(log_path):
    """Parse Log-Datei und extrahiere Training-Stats."""
    try:
        with open(log_path, 'r') as f:
            content = f.read()

        # Suche nach wichtigen Informationen
        stats = {
            'current_reward': None,
            'current_experiment': None,
            'total_steps': None,
            'eval_return': None,
            'started': False,
            'completed': False,
        }

        # Check if started
        if "PPO SYSTEMATIC OPTIMIZATION" in content or "=== DQN Training Start ===" in content:
            stats['started'] = True

        # Extract current experiment (reward type)
        experiment_match = re.findall(r'EXPERIMENT \d+/4: (\w+)', content)
        if experiment_match:
            stats['current_experiment'] = experiment_match[-1]

        # Extract training steps
        steps_matches = re.findall(r'(\d+) timesteps', content)
        if steps_matches:
            stats['total_steps'] = int(steps_matches[-1])

        # Extract eval returns
        eval_matches = re.findall(r'Mean Return: ([-\d.]+)%', content)
        if eval_matches:
            stats['eval_return'] = float(eval_matches[-1])

        # Check if completed
        if "OPTIMIZATION COMPLETE" in content or "Training Complete" in content:
            stats['completed'] = True

        return stats

    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Fehler beim Parsen: {e}")
        return None


def find_latest_log():
    """Finde neueste Log-Datei."""
    log_dir = Path("/tmp")

    # Suche nach Optimization Logs
    opt_logs = list(log_dir.glob("ppo_optimization_*.log"))

    if opt_logs:
        latest = max(opt_logs, key=lambda p: p.stat().st_mtime)
        return latest

    return None


def display_progress(stats, log_file):
    """Zeige Progress schön formatiert an."""
    print("\n" + "="*60)
    print("🤖 TRAINING PROGRESS MONITOR")
    print("="*60)
    print(f"Zeit: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Log-Datei: {log_file.name}")
    print("-"*60)

    if not stats:
        print("❌ Keine Training-Daten gefunden")
        print("Warte auf Training-Start...")
        return

    if not stats['started']:
        print("⏳ Training noch nicht gestartet...")
        return

    print("✅ Training läuft!")
    print()

    if stats['current_experiment']:
        print(f"📍 Aktuelles Experiment: {stats['current_experiment'].upper()}")

    if stats['total_steps']:
        progress = (stats['total_steps'] / 500_000) * 100
        bar_length = 40
        filled = int(bar_length * stats['total_steps'] / 500_000)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"📊 Fortschritt: [{bar}] {progress:.1f}%")
        print(f"   Steps: {stats['total_steps']:,} / 500,000")

    if stats['eval_return'] is not None:
        print(f"💰 Letzte Evaluation: {stats['eval_return']:+.2f}%")

    if stats['completed']:
        print()
        print("🎉 TRAINING ABGESCHLOSSEN!")

    print("="*60)
    print()


def main():
    """Hauptfunktion - Live Monitoring."""
    print("\n�� Training Progress Monitor gestartet")
    print("Drücke Ctrl+C zum Beenden\n")

    try:
        while True:
            # Finde neueste Log-Datei
            log_file = find_latest_log()

            if not log_file:
                print("⏳ Warte auf Log-Datei...")
                time.sleep(5)
                continue

            # Parse Stats
            stats = parse_log_file(log_file)

            # Display
            display_progress(stats, log_file)

            # Check if done
            if stats and stats['completed']:
                print("✅ Training abgeschlossen - Monitor beendet")
                break

            # Wait before next update
            print("(Aktualisiert alle 30 Sekunden...)")
            time.sleep(30)

            # Clear screen (optional)
            print("\033[2J\033[H")  # ANSI clear screen

    except KeyboardInterrupt:
        print("\n\n👋 Monitor beendet")
    except Exception as e:
        logger.error(f"Fehler: {e}")


if __name__ == "__main__":
    main()
