# Docker Setup for Solana RL Trading Bot

This directory contains Docker configuration for TimescaleDB, the time-series database used by the trading bot.

## Overview

- **TimescaleDB**: PostgreSQL with TimescaleDB extension for efficient time-series data storage
- **pgAdmin** (optional): Web-based database management interface
- **Automatic Backups**: Configured backup directory for database dumps

## Prerequisites

- Docker Desktop installed and running
- At least 4GB RAM available for Docker
- At least 10GB disk space

## Quick Start

### 1. Start the Database

```bash
# From project root
cd docker
docker-compose up -d

# Or using Make
make docker-up
```

### 2. Verify Database is Running

```bash
# Check container status
docker-compose ps

# Should show:
# NAME                       STATUS              PORTS
# solana-rl-timescaledb      Up (healthy)        0.0.0.0:5432->5432/tcp
```

### 3. Check Logs

```bash
# View database logs
docker-compose logs -f timescaledb

# Should see:
# "Database initialization completed!"
```

### 4. Test Database Connection

```bash
# From project root
python scripts/test_database.py
```

## Configuration

### Environment Variables

The database uses these environment variables (from [.env](.env)):

```bash
TIMESCALE_HOST=localhost
TIMESCALE_PORT=5432
TIMESCALE_DB=trading_bot
TIMESCALE_USER=postgres
TIMESCALE_PASSWORD=changeme  # CHANGE THIS!
```

### Performance Tuning

Adjust these in [docker-compose.yml](docker-compose.yml) based on your system:

```yaml
environment:
  POSTGRES_SHARED_BUFFERS: 512MB       # 25% of RAM
  POSTGRES_EFFECTIVE_CACHE_SIZE: 2GB   # 50% of RAM
  POSTGRES_MAX_CONNECTIONS: 100
  POSTGRES_WORK_MEM: 16MB
```

### Resource Limits

Current limits (adjust for your system):

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '0.5'
      memory: 1G
```

## Using pgAdmin (Optional)

pgAdmin provides a web interface for database management.

### Start pgAdmin

```bash
# Start with tools profile
docker-compose --profile tools up -d

# Or start everything
docker-compose --profile tools up -d
```

### Access pgAdmin

1. Open browser: http://localhost:5050
2. Login:
   - Email: `admin@admin.com`
   - Password: `admin`
3. Add Server:
   - Host: `timescaledb`
   - Port: `5432`
   - Database: `trading_bot`
   - Username: `postgres`
   - Password: (from .env)

## Database Schema

The database includes these tables:

### Time-Series Tables (Hypertables)

- **ohlcv**: Market OHLCV data (Open, High, Low, Close, Volume)
- **features**: Calculated technical indicators
- **performance**: Strategy performance metrics over time
- **data_quality**: Data quality monitoring
- **system_logs**: Application logs

### Regular Tables

- **trades**: Executed trades (buy/sell transactions)
- **models**: ML model metadata and tracking

## Common Operations

### Stop the Database

```bash
cd docker
docker-compose down

# Or
make docker-down
```

### Restart the Database

```bash
docker-compose restart
```

### View Logs

```bash
# All logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# Specific service
docker-compose logs timescaledb
```

### Access Database Shell

```bash
# PostgreSQL shell
docker exec -it solana-rl-timescaledb psql -U postgres -d trading_bot

# Once inside:
\dt              # List tables
\d ohlcv         # Describe ohlcv table
\dx              # List extensions (should show timescaledb)
SELECT * FROM timescaledb_information.hypertables;  # Show hypertables
\q               # Exit
```

## Backup & Restore

### Manual Backup

```bash
# Create backup
docker exec solana-rl-timescaledb pg_dump -U postgres trading_bot > ./backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Or use the included script
./backup_database.sh
```

### Restore from Backup

```bash
# Stop the database
docker-compose down

# Remove old data
docker volume rm docker_timescaledb_data

# Start fresh
docker-compose up -d

# Wait for initialization
sleep 10

# Restore
cat ./backups/backup_YYYYMMDD_HHMMSS.sql | docker exec -i solana-rl-timescaledb psql -U postgres -d trading_bot
```

### Automated Backups

Backups are stored in `./backups/` directory.

To set up automated daily backups, add a cron job:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/solana-rl-bot/docker && docker exec solana-rl-timescaledb pg_dump -U postgres trading_bot > ./backups/backup_$(date +\%Y\%m\%d).sql
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs timescaledb

# Check if port 5432 is already in use
lsof -i :5432

# Remove and recreate
docker-compose down -v
docker-compose up -d
```

### Health Check Failing

```bash
# Check database is ready
docker exec solana-rl-timescaledb pg_isready -U postgres

# If not ready, wait and retry
# Database initialization can take 30-60 seconds
```

### Connection Refused

1. Ensure container is running: `docker-compose ps`
2. Check health status: `docker-compose ps` (should show "healthy")
3. Verify port mapping: `docker port solana-rl-timescaledb`
4. Check logs: `docker-compose logs timescaledb`

### Out of Memory

If you see OOM errors:

1. Reduce `POSTGRES_SHARED_BUFFERS` in docker-compose.yml
2. Reduce resource limits
3. Increase Docker memory allocation in Docker Desktop settings

### Slow Queries

1. Check hypertables are created:
   ```sql
   SELECT * FROM timescaledb_information.hypertables;
   ```

2. Check indexes:
   ```sql
   \di
   ```

3. Analyze query performance:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM ohlcv WHERE symbol = 'SOL/USDT' LIMIT 1000;
   ```

## Data Retention

The database automatically cleans up old data using retention policies:

- **OHLCV data**: 2 years
- **Features**: 2 years
- **Performance metrics**: 3 years
- **Data quality logs**: 6 months
- **System logs**: 90 days

Check retention policies:

```sql
SELECT * FROM timescaledb_information.jobs WHERE proc_name = 'policy_retention';
```

## Maintenance

### Vacuum Database

```bash
# Vacuum to reclaim space
docker exec solana-rl-timescaledb psql -U postgres -d trading_bot -c "VACUUM ANALYZE;"
```

### Check Database Size

```bash
docker exec solana-rl-timescaledb psql -U postgres -d trading_bot -c "
SELECT
    pg_size_pretty(pg_database_size('trading_bot')) as total_size,
    pg_size_pretty(pg_total_relation_size('ohlcv')) as ohlcv_size,
    pg_size_pretty(pg_total_relation_size('features')) as features_size;
"
```

### Monitor Chunk Usage

TimescaleDB automatically partitions data into chunks:

```sql
SELECT
    hypertable_name,
    chunk_name,
    range_start,
    range_end
FROM timescaledb_information.chunks
ORDER BY hypertable_name, range_start DESC
LIMIT 20;
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Change default password** in `.env` before production use
2. **Never commit** `.env` to git
3. **Use strong passwords** for production
4. **Restrict port 5432** to localhost only in production (remove port mapping)
5. **Enable SSL** for production deployments
6. **Regular backups** - test restore procedures

## Performance Tips

1. **Adjust chunk intervals** based on data volume
2. **Create appropriate indexes** for your queries
3. **Use continuous aggregates** for frequently accessed summaries
4. **Monitor query performance** with EXPLAIN ANALYZE
5. **Keep statistics up to date** with ANALYZE

## Additional Resources

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [pgAdmin Documentation](https://www.pgadmin.org/docs/)

## Support

For issues:

1. Check logs: `docker-compose logs`
2. Verify health: `docker-compose ps`
3. Test connection: `python scripts/test_database.py`
4. Review this README
5. Check TimescaleDB documentation

---

**Last updated**: 2025-12-07
