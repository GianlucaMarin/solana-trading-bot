.PHONY: help setup install install-dev test lint format typecheck check clean docker-up docker-down download-data train backtest paper-trading

# Default target
help:
	@echo "🚀 Solana RL Trading Bot - Makefile Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Create venv and install dependencies"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make test           - Run tests with coverage"
	@echo "  make lint           - Run linting (ruff)"
	@echo "  make format         - Format code (black + ruff)"
	@echo "  make typecheck      - Run type checking (mypy)"
	@echo "  make check          - Run all quality checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start TimescaleDB"
	@echo "  make docker-down    - Stop TimescaleDB"
	@echo ""
	@echo "Data & Training:"
	@echo "  make download-data  - Download historical data"
	@echo "  make train          - Train PPO agent"
	@echo "  make backtest       - Run backtesting"
	@echo "  make paper-trading  - Start paper trading"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Clean cache and temp files"

# Setup virtual environment
setup:
	@echo "📦 Creating virtual environment..."
	python3.11 -m venv venv
	@echo "📥 Installing dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r requirements-dev.txt
	@echo "✅ Setup completed!"
	@echo ""
	@echo "Activate with: source venv/bin/activate"

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=src/solana_rl_bot --cov-report=term-missing --cov-report=html

# Lint code
lint:
	@echo "🔍 Linting code..."
	ruff check src/ tests/

# Format code
format:
	@echo "✨ Formatting code..."
	black src/ tests/ scripts/
	ruff check --fix src/ tests/
	@echo "✅ Code formatted!"

# Type checking
typecheck:
	@echo "🔎 Type checking..."
	mypy src/

# Run all checks
check: lint typecheck test
	@echo "✅ All checks passed!"

# Clean cache and temporary files
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage
	@echo "✅ Cleanup completed!"

# Docker commands
docker-up:
	@echo "🐳 Starting TimescaleDB..."
	cd docker && docker-compose up -d
	@echo "✅ Database started on localhost:5432"

docker-down:
	@echo "🛑 Stopping TimescaleDB..."
	cd docker && docker-compose down
	@echo "✅ Database stopped"

# Download historical data
download-data:
	@echo "📥 Downloading historical data..."
	python scripts/download_data.py --symbol SOL/USDT --days 365

# Train agent
train:
	@echo "🤖 Training PPO agent..."
	python scripts/train_agent.py --agent ppo --timesteps 100000 --tensorboard

# Run backtest
backtest:
	@echo "📊 Running backtest..."
	python scripts/run_backtest.py --strategy sma_crossover --start 2023-01-01 --end 2024-01-01

# Start paper trading
paper-trading:
	@echo "🔴 Starting paper trading..."
	python scripts/start_paper_trading.py --agent ppo --model models/production/ppo_best.zip

# Initialize database (run migrations)
init-db: docker-up
	@echo "⏳ Waiting for database to be ready..."
	sleep 5
	@echo "✅ Database initialized!"
