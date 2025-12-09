# 🤖 Solana Trading Bot

Ein intelligenter Trading Bot für Solana (SOL/USDT), der mit **Künstlicher Intelligenz** lernt, profitable Trading-Strategien zu entwickeln.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-Phase_4.2_Complete-brightgreen.svg)

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

#### 3.5 Risk Management (Solana-optimiert)

Solana ist extrem volatil - deshalb haben wir ein spezielles Risk Management System entwickelt:

| Parameter | 5min Timeframe | Warum? |
|-----------|---------------|--------|
| **Stop-Loss** | -8% | SOL kann schnell 10%+ fallen |
| **Take-Profit** | +15% | Gewinne mitnehmen bevor Reversal |
| **Trailing Stop** | 4% (ab +6%) | Gewinne absichern |
| **Max Position** | 25% | Nie alles auf eine Karte |
| **Max Daily Loss** | -8% | Tages-Verlust begrenzen |
| **Max Drawdown** | -20% | Gesamtverlust limitieren |

**Warum Solana-spezifisch?**
- SOL hat 3-5x höhere Volatilität als Bitcoin
- Standard-Werte (2% Stop-Loss) werden sofort ausgelöst
- Unsere Werte sind auf SOL's Bewegungsmuster kalibriert

### **Phase 4: KI-Algorithmen Vergleich** ✅

Wir haben drei verschiedene Reinforcement Learning Algorithmen implementiert, trainiert und verglichen:

#### 🤖 Die drei Algorithmen

| Algorithmus | Typ | Wie funktioniert es? |
|-------------|-----|---------------------|
| **PPO** | Policy-based | Lernt direkt "was soll ich tun?" - optimiert die Strategie direkt |
| **DQN** | Value-based | Lernt "wie gut ist jede Action?" - erstellt Wertetabelle |
| **SAC** | Actor-Critic | Kombiniert beide + automatische Exploration durch Entropy |

**PPO (Proximal Policy Optimization)**
- Lernt durch "Trial & Error" welche Actions gut sind
- Sehr stabil und robust beim Training
- Ideal für diskrete Entscheidungen (Buy/Hold/Sell)

**DQN (Deep Q-Network)**
- Erstellt eine Wertetabelle für jede Action
- Verwendet Experience Replay (lernt aus vergangenen Erfahrungen)
- Gut bei klaren, diskreten Entscheidungen

**SAC (Soft Actor-Critic)**
- State-of-the-art für kontinuierliche Control-Tasks
- Maximiert Reward UND Exploration gleichzeitig
- 6 neuronale Netze (komplexer, aber oft leistungsfähiger)

#### 📊 Vergleichs-Ergebnisse

Alle drei Agents wurden fair auf **identischen Test-Daten** verglichen:
- **Test-Zeitraum:** Sept-Dez 2025 (SOL Crash von $203 → $134)
- **Markt-Performance:** -34% (Buy & Hold)

| Agent | Portfolio Return | Crash vermieden |
|-------|-----------------|-----------------|
| **PPO** | **-3.9%** | 88% ✅ |
| DQN | -11.2% | 67% |
| SAC | -17.2% | 50% |
| Markt | -34.3% | 0% |

#### 🏆 Warum PPO gewonnen hat

1. **Beste Performance:** Nur -3.9% in einem -34% Crash
2. **Diskrete Actions:** Trading ist Buy/Hold/Sell - perfekt für PPO
3. **Stabilität:** On-policy Learning ist robuster bei volatilen Märkten
4. **SAC-Problem:** SAC braucht kontinuierliche Actions, unser Trading ist aber diskret

**Fazit:** PPO ist unser Winner und wird für alle weiteren Timeframes verwendet!

---

## 🔬 Wie funktioniert das Lernen?

### Schritt 1: Daten sammeln
```bash
python scripts/download_real_data.py
```
Lädt **12 Monate echte SOL/USDT Daten** von Binance API
- 104.921 Candles (5-Minuten-Intervalle)
- Echte Marktdaten, keine Synthetik!

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

Nach 500.000 Training-Steps auf echten Daten hat der Bot profitable Muster erkannt! 🎉

---

## 📊 Aktuelle Performance

**Test-Szenario:** SOL/USDT Crash Sept-Dez 2025 (-34%)

| Agent | Return | vs. Markt |
|-------|--------|-----------|
| Buy & Hold | -34.3% | Baseline |
| **PPO** | **-3.9%** | +30% besser ✅ |
| DQN | -11.2% | +23% besser |
| SAC | -17.2% | +17% besser |

**Erklärung:**
- Alle Agents haben den **-34% Crash** deutlich abgefedert
- **PPO** hat 88% des Verlustes vermieden - der beste Agent!
- Das zeigt: Die KI hat gelernt, Risiko zu managen

---

## 🛠️ Verwendete Technologien

| Was | Technologie |
|-----|------------|
| **Programmiersprache** | Python 3.10+ |
| **KI Framework** | Stable-Baselines3 (PPO, DQN, SAC) |
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
- [x] **Phase 4:** KI-Algorithmen (PPO, DQN, SAC) → Winner: PPO
- [ ] **Phase 5:** Hyperparameter Tuning (Optuna)
- [ ] **Phase 6:** Multi-Timeframe Ensemble
- [ ] **Phase 7:** Paper Trading (4+ Wochen)
- [ ] **Phase 8:** Live Trading

**Aktueller Stand:** Phase 4 abgeschlossen - PPO als bester Algorithmus ausgewählt!

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

**Status:** 🟢 Phase 4 komplett - PPO als Winner ausgewählt!

**Letztes Update:** Dezember 2025
