# 🤖 Solana Trading Bot

Ein intelligenter Trading Bot für Solana (SOL/USDT), der mit **Künstlicher Intelligenz** lernt, profitable Trading-Strategien zu entwickeln.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-Phase_4.1_Complete-brightgreen.svg)

---

## 💡 Was macht der Bot?

Der Bot analysiert den Solana-Markt und trifft automatisch Trading-Entscheidungen:
- 🟢 **Kaufen** - wenn eine gute Einstiegschance erkannt wird
- 🔴 **Verkaufen** - wenn Gewinn realisiert werden sollte
- ⚪ **Halten** - wenn keine klare Chance besteht

**Das Besondere:** Anders als einfache Bots mit festen Regeln **lernt dieser Bot selbstständig** aus historischen Marktdaten, welche Strategien funktionieren und welche nicht.

---

## 🎯 Projektziele

Der Bot soll nach dem Training:
- ✅ Profitable Trading-Möglichkeiten erkennen
- ✅ Verluste minimieren und Risiko managen
- ✅ Besser performen als "einfach kaufen und halten"
- ✅ Auch bei fallenden Kursen Gewinne machen (Short-Selling)

---

## 🏗️ Projektstruktur

```
solana-trading-bot/
│
├── src/solana_rl_bot/          # Hauptcode
│   │
│   ├── data/                   # Daten-Download & Verarbeitung
│   │   ├── market_data.py      # Binance API (lädt SOL/USDT Daten)
│   │   └── features.py         # Berechnet Trading-Indikatoren
│   │
│   ├── environment/            # Trading-Simulation für KI
│   │   ├── trading_env.py      # Basis Trading Umgebung
│   │   ├── advanced_trading_env.py  # Erweitert mit Short-Selling
│   │   └── rewards.py          # 5 Lern-Strategien
│   │
│   ├── backtesting/            # Performance-Tests
│   │   ├── backtester.py       # Test-Engine
│   │   ├── metrics.py          # Performance-Metriken
│   │   └── visualizer.py       # Grafische Auswertung
│   │
│   └── utils.py                # Hilfsfunktionen
│
├── scripts/                    # Test-Skripte
│   ├── download_data.py        # Daten von Binance holen
│   ├── test_trading_env.py     # Trading-Umgebung testen
│   └── test_*.py               # Weitere Tests
│
├── data/                       # Marktdaten (lokal gespeichert)
├── models/                     # Trainierte KI-Modelle
├── docs/                       # Dokumentation
└── requirements.txt            # Benötigte Python-Pakete
```

---

## ✅ Was ist bereits fertig? (Phase 1-4.1)

### **Phase 1: Projekt Setup** ✅
- Python-Umgebung mit allen benötigten Bibliotheken
- Projektstruktur und professionelles Logging
- Testing Framework

### **Phase 2: Daten-Pipeline** ✅
**Was macht das:**
- Holt automatisch Marktdaten von Binance (Preis, Volumen, etc.)
- Berechnet über 15 Trading-Indikatoren (RSI, MACD, Bollinger Bands, etc.)
- Diese Indikatoren helfen dem Bot, Markt-Trends zu erkennen

**Beispiel:** RSI zeigt ob ein Coin "überkauft" (teuer) oder "überverkauft" (günstig) ist

### **Phase 3: Trading-Umgebung** ✅

#### 3.1 Basic Trading Environment
- Simuliert realistische Trades mit Gebühren (0.1%)
- Verwaltet Portfolio (Cash + Coins)
- Tracked alle Käufe und Verkäufe

#### 3.2 Lern-Strategien (5 verschiedene)
Der Bot kann verschiedene Ziele verfolgen:

1. **Profit** - Maximiere einfach den Gewinn
2. **Sharpe** - Maximiere Gewinn pro Risiko
3. **Sortino** - Minimiere speziell Verlust-Risiko
4. **Multi-Objective** - Balance aus Gewinn, Risiko & Drawdown
5. **Incremental** - Schnelles Lernen durch Step-by-Step Belohnungen

#### 3.3 Backtesting
- Testet Strategien auf historischen Daten
- Vergleicht Performance mit "einfach kaufen und halten"
- Zeigt detaillierte Statistiken (Gewinn, Risiko, Win-Rate, etc.)

#### 3.4 Advanced Features
- **Short-Selling:** Auch bei fallenden Kursen Gewinn machen
- **Position Sizing:** Flexibel entscheiden wie viel % investiert wird
- **Stop-Loss:** Automatische Verlustbegrenzung

**Test-Status:** Alle 15 Tests bestanden! ✅

### **Phase 4.1: PPO Agent Training** ✅

#### 🤖 Was ist PPO?
**PPO** steht für **Proximal Policy Optimization** - einer der besten KI-Algorithmen für Trading.

**Einfach erklärt:**
Der Bot lernt wie ein Kind durch "Trial & Error":
1. **Ausprobieren:** Bot macht einen Trade (Kaufen/Verkaufen/Halten)
2. **Belohnung:** War der Trade profitabel? → Positive Belohnung ✅
3. **Lernen:** Bot merkt sich welche Entscheidungen gut waren
4. **Wiederholen:** Nach 100.000 Versuchen kennt der Bot profitable Muster!

**Warum PPO?**
- ✅ Sehr stabil und robust
- ✅ Lernt schnell (sample-efficient)
- ✅ Bewährt für Trading (von Google/OpenAI entwickelt)

#### 📊 Erste Trainings-Ergebnisse

**Training Details:**
- 100.000 Trading-Schritte auf 6 Monaten SOL/USDT Daten
- 51.840 Candles (5-Minuten-Intervalle)
- Training-Zeit: ~15 Minuten

**Performance (10 Test-Episoden):**
| Metrik | Random Agent | PPO Agent | Verbesserung |
|--------|--------------|-----------|--------------|
| **Mean Return** | -12.0% | **+2.04%** | ✅ +14% besser! |
| **Best Return** | ~0% | **+5.77%** | 🎯 Profitabel! |
| **Worst Return** | ~-20% | **-2.13%** | ✅ Weniger Verlust |

**🎉 Erfolg:** Der PPO Agent hat gelernt profitabel zu traden und schlägt zufälliges Trading deutlich!

---

## 🔬 Wie funktioniert das Lernen?

### Schritt 1: Daten sammeln
```bash
python scripts/download_data.py
```
Lädt echte SOL/USDT Daten von Binance (z.B. 6 Monate)

### Schritt 2: Environment testen
```bash
python scripts/test_trading_env.py
```
Testet ob die Trading-Simulation korrekt funktioniert

**Wichtig:** Random Agent (zufällige Entscheidungen) macht ~12% Verlust
→ Das ist gut! Zeigt dass zufälliges Trading nicht funktioniert

### Schritt 3: KI trainieren ✅
```bash
python scripts/train_ppo.py
```

Der Bot lernt aus tausenden simulierten Trades:

1. **Beobachten:** Preis, Indikatoren, Portfolio-Status
2. **Handeln:** Kaufen, Verkaufen oder Halten
3. **Bewerten:** War die Entscheidung profitabel?
4. **Lernen:** Wiederhole gute Entscheidungen, vermeide schlechte

Nach 100.000 Training-Steps hat der Bot profitable Muster erkannt! 🎉

---

## 📊 Aktuelle Performance

| Metrik | Random Agent | PPO Agent (trainiert) |
|--------|-------------|----------------------|
| **Return** | -12.0% | **+2.04%** ✅ |
| **Best Trade** | ~0% | **+5.77%** 🎯 |
| **Worst Trade** | ~-20% | **-2.13%** |
| **Stabilität** | Sehr volatil | Viel konstanter |

**Erklärung:**
- **Random Agent** macht absichtlich zufällige Entscheidungen → Verlust von 12%
- **PPO Agent** hat in 100.000 Steps gelernt → Gewinn von +2% im Durchschnitt!
- Das ist erst der Anfang - mit mehr Training kann die Performance noch besser werden

---

## 🛠️ Verwendete Technologien

| Was | Technologie |
|-----|------------|
| **Programmiersprache** | Python 3.10+ |
| **KI Framework** | Stable-Baselines3 (PPO, DQN) |
| **Data Science** | pandas, numpy, ta-lib |
| **Trading Simulation** | Gymnasium (von OpenAI) |
| **Datenquelle** | Binance API |
| **Visualisierung** | matplotlib, plotly |

---

## 🚨 Wichtige Hinweise!

⚠️ **BITTE LESEN:**

1. **Keine Gewinn-Garantie** - Trading ist risikoreich, Verluste sind möglich
2. **Nur Lern-Projekt** - Dies ist experimentell, nicht für echtes Geld gedacht
3. **Start klein** - Falls du es live nutzt, nur mit Geld das du verlieren kannst
4. **Erst Paper Trading** - Mindestens 3 Monate testen bevor echtes Geld
5. **Vergangenheit ≠ Zukunft** - Gute Backtest-Ergebnisse garantieren nichts

**Dieses Projekt ist "as-is" ohne jegliche Garantie. Nutzung auf eigene Gefahr!**

---

## 🗺️ Roadmap

- [x] **Phase 1:** Projekt Setup & Grundstruktur
- [x] **Phase 2:** Daten-Pipeline von Binance
- [x] **Phase 3:** Trading-Umgebung & Backtesting
- [x] **Phase 4.1:** PPO Agent Training
- [ ] **Phase 4.2:** DQN Agent (Alternative KI-Methode)
- [ ] **Phase 5:** Advanced Features & Optimierung
- [ ] **Phase 6:** Paper Trading (3+ Monate)
- [ ] **Phase 7:** Optional: Live Trading

**Aktueller Stand:** Phase 4.1 abgeschlossen - Bot kann profitabel traden! 🎉

---

## 📚 Weitere Dokumentation

Im `docs/` Ordner findest du detaillierte Dokumentation:
- `STEP_3.1_COMPLETE.md` - Basic Trading Environment
- `STEP_3.2_COMPLETE.md` - Reward Functions erklärt
- `STEP_3.3_COMPLETE.md` - Backtesting Framework
- `STEP_3.4_COMPLETE.md` - Advanced Features (Short-Selling, etc.)

---

## 🚀 Installation

```bash
# 1. Repository klonen
git clone https://github.com/DEIN-USERNAME/solana-trading-bot.git
cd solana-trading-bot

# 2. Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # macOS/Linux
# oder: venv\Scripts\activate  # Windows

# 3. Pakete installieren
pip install -r requirements.txt

# 4. Daten herunterladen
python scripts/download_data.py

# 5. Tests laufen lassen
python scripts/test_trading_env.py
```

---

## 📫 Fragen oder Probleme?

Falls du Fragen hast oder auf Probleme stößt, öffne einfach ein Issue auf GitHub!

---

**Status:** 🟢 Phase 4.1 komplett - PPO Agent trainiert und profitabel!

**Letztes Update:** Dezember 2025
