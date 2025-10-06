# API-Based Batch Monitoring

**No SSH required!** Monitor batch processing via REST API endpoints.

## Quick Start

### Local Development
```bash
# Start local server first
uv run python run.py

# In another terminal, run the monitor
python scripts/api_batch_monitor.py
```

### Railway Production
```bash
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app
```

## Usage Examples

### Basic Commands
```bash
# Monitor all portfolios (local)
python scripts/api_batch_monitor.py

# Monitor specific portfolio (Railway)
python scripts/api_batch_monitor.py \
  --url https://sigmasight-be-production.up.railway.app \
  --portfolio-id 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe

# Force run even if batch already running
python scripts/api_batch_monitor.py --force

# Custom polling interval (5 seconds)
python scripts/api_batch_monitor.py --poll-interval 5

# Longer timeout for full batch runs
python scripts/api_batch_monitor.py --max-duration 1200  # 20 minutes
```

### Custom Authentication
```bash
python scripts/api_batch_monitor.py \
  --url https://sigmasight-be-production.up.railway.app \
  --email your_email@example.com \
  --password your_password
```

## Output Example

```
🔐 Authenticating as demo_individual@sigmasight.com...
✅ Authentication successful

🚀 Triggering batch run for all portfolios...
✅ Batch started: 84728a8c-f7ac-4c72-a7cb-8cdb212198c4
📊 Poll URL: /api/v1/admin/batch/run/current

📡 Monitoring progress (polling every 3s)...
================================================================================
[13:28:36] [████████████░░░░░░░░░░░░░░░░] 37.5% | 2m 15s | 3/8 jobs | position_values_update_1d8ddd95...
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--url` | `http://localhost:8000` | Base URL of API server |
| `--email` | `demo_individual@sigmasight.com` | Email for authentication |
| `--password` | `demo12345` | Password for authentication |
| `--portfolio-id` | (all) | Specific portfolio UUID to process |
| `--force` | False | Force run even if batch already running |
| `--poll-interval` | 3 | Polling interval in seconds |
| `--max-duration` | 600 | Maximum monitoring duration (10 minutes) |

## API Endpoints Used

The script interacts with these endpoints:

1. **Authentication**
   - `POST /api/v1/auth/login` - Get JWT token

2. **Batch Control**
   - `POST /api/v1/admin/batch/run` - Trigger batch processing
   - `GET /api/v1/admin/batch/run/current` - Poll current status

## Progress Display

The script shows real-time progress with:
- **Progress Bar**: Visual representation (█ for completed, ░ for pending)
- **Percentage**: Overall completion (0-100%)
- **Duration**: Elapsed time in human-readable format
- **Job Count**: Completed/Total jobs
- **Current Job**: Name of currently executing job
- **Timestamp**: Local time of each update

## Exit Codes

- `0` - Success (batch completed)
- `1` - Failure (authentication failed, trigger failed, or error)

## Notes

- Script uses polling (default: 3 seconds) to check progress
- JWT token expires after 24 hours (86400 seconds)
- Batch runs prevent concurrent execution (use `--force` to override)
- Market data sync jobs can take 30-60 seconds
- Full batch runs typically take 3-5 minutes per portfolio

## Troubleshooting

### "Connection refused" Error
- **Local**: Make sure `uv run python run.py` is running first
- **Railway**: Check that Railway service is deployed and healthy

### "401 Unauthorized" Error
- Verify email/password are correct
- Check that demo user exists in the database

### "409 Batch already running" Error
- Wait for current batch to complete, or
- Use `--force` flag to override (not recommended)

### Timeout Before Completion
- Increase `--max-duration` for full batch runs
- Full runs can take 5-20 minutes depending on portfolio size

## Integration Examples

### Simple Monitoring Script
```bash
#!/bin/bash
# monitor_railway_batch.sh
python scripts/api_batch_monitor.py \
  --url https://sigmasight-be-production.up.railway.app \
  --max-duration 1200
```

### Cron Job (Daily at 2 AM)
```bash
0 2 * * * cd /path/to/backend && python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app
```

### Python Integration
```python
from scripts.api_batch_monitor import BatchMonitor

monitor = BatchMonitor(
    base_url="https://sigmasight-be-production.up.railway.app",
    email="demo_individual@sigmasight.com",
    password="demo12345"
)

success = monitor.run(
    portfolio_id="1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe",
    poll_interval=5,
    max_duration=600
)
```

## Related Documentation

- **Batch Orchestrator**: `app/batch/batch_orchestrator_v2.py`
- **Batch Tracker**: `app/batch/batch_run_tracker.py`
- **Admin Endpoints**: `app/api/v1/endpoints/admin_batch.py`
- **API Router**: `app/api/v1/router.py`
