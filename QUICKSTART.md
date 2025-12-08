# 🚀 Quick Start Guide

Welcome to the Solana RL Trading Bot project! This guide will help you get started in minutes.

---

## ✅ Prerequisites

- **Python 3.11+** installed
- **Docker** installed (for TimescaleDB)
- **Git** installed
- Binance API Keys (optional for now)

---

## 📦 Step 1: Setup Environment

```bash
# Navigate to project directory
cd solana-rl-bot

# Create virtual environment and install dependencies
make setup

# Or manually:
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

---

## 🔧 Step 2: Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Minimum required (for local development):**
```env
TIMESCALE_PASSWORD=your_secure_password
LOG_LEVEL=INFO
```

---

## 🐳 Step 3: Start Database

```bash
# Start TimescaleDB
make docker-up

# Or manually:
cd docker
docker-compose up -d

# Verify it's running
docker-compose ps
```

The database will be available at `localhost:5432` with the schema automatically initialized.

---

## 📊 Step 4: Verify Installation

```bash
# Activate virtual environment (if not already)
source venv/bin/activate

# Run tests
make test

# Check code quality
make check
```

---

## 🎯 Next Steps

### Option A: Explore with Jupyter Notebooks

```bash
# Start Jupyter
jupyter notebook

# Open notebooks in the notebooks/ directory:
# - 01_data_exploration.ipynb
# - 02_feature_engineering.ipynb
```

### Option B: Download Historical Data

```bash
# Download SOL/USDT data for the last year
make download-data

# Or with custom parameters:
python scripts/download_data.py --symbol SOL/USDT --days 365 --timeframes 5m,15m,1h,4h
```

### Option C: Run Baseline Strategies

```bash
# Backtest SMA Crossover strategy
make backtest

# Or with custom parameters:
python scripts/run_backtest.py \
  --strategy sma_crossover \
  --start 2023-01-01 \
  --end 2024-01-01
```

### Option D: Train Your First RL Agent

```bash
# Train PPO agent
make train

# Or with custom parameters:
python scripts/train_agent.py \
  --agent ppo \
  --timesteps 100000 \
  --tensorboard
```

---

## 📁 Project Structure

See [PROJECT_STRUCTURE.txt](PROJECT_STRUCTURE.txt) for complete directory layout.

**Key directories:**
- `src/solana_rl_bot/` - Main Python package
- `configs/` - Configuration files
- `data/` - Data storage (OHLCV, features)
- `models/` - Saved RL models
- `logs/` - Log files
- `scripts/` - Utility scripts
- `tests/` - Unit tests

---

## 🛠️ Useful Commands

```bash
# Development
make format          # Format code with black
make lint            # Lint code with ruff
make typecheck       # Type checking with mypy
make test            # Run tests with coverage

# Data & Training
make download-data   # Download historical data
make train           # Train RL agent
make backtest        # Run backtesting

# Docker
make docker-up       # Start TimescaleDB
make docker-down     # Stop TimescaleDB

# Cleanup
make clean           # Clean cache files
```

---

## 🎓 Learning Path

**Week 1: Foundation**
1. ✅ Setup environment
2. ✅ Explore data with notebooks
3. ✅ Understand baseline strategies
4. ✅ Run your first backtest

**Week 2: Data Pipeline**
1. Implement data collectors
2. Build feature engineering pipeline
3. Set up database storage
4. Validate data quality

**Week 3: Trading Environment**
1. Build Gymnasium environment
2. Implement reward function
3. Add risk management
4. Create backtesting environment

**Week 4: RL Training**
1. Train PPO agent
2. Evaluate performance
3. Compare against baselines
4. Optimize hyperparameters

**Weeks 5+: Advanced Features**
- Multi-timeframe analysis
- Ensemble methods
- Paper trading
- Live trading preparation

---

## 🆘 Troubleshooting

### Database won't start
```bash
# Check if port 5432 is already in use
lsof -i :5432

# Stop and restart
make docker-down
make docker-up
```

### Import errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Tests failing
```bash
# Check Python version
python --version  # Should be 3.11+

# Run tests with verbose output
pytest tests/ -v
```

---

## 📚 Resources

- [README.md](README.md) - Project overview
- [Masterplan](../MASTERPLAN.md) - Detailed implementation plan
- [Documentation](docs/) - Detailed guides

---

## 🎯 Phase 1 Checklist

- [x] Project structure created
- [x] Virtual environment setup
- [x] Dependencies installed
- [x] Database running
- [ ] Configuration customized
- [ ] Data collector implemented
- [ ] First backtest run

---

**Ready to build something amazing? Let's go! 🚀**

For questions or issues, check the README or open an issue on GitHub.
