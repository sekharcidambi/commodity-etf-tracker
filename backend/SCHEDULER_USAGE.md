# Scheduler Service Usage Guide

## Overview

The `scheduler_service.py` manages automated data collection jobs using APScheduler. It handles scheduling, execution tracking, error handling, and retry logic for all data collection operations.

## Files Created

1. `/backend/app/services/scheduler_service.py` - Main scheduler service
2. `/backend/app/models/data_jobs.py` - Database model for job tracking

## Scheduled Jobs

| Job Name | Schedule | Description |
|----------|----------|-------------|
| `daily_price_collection` | Daily at 5:00 PM ET | Collect ETF and futures prices after market close |
| `weekly_flow_collection` | Friday at 6:00 PM ET | Collect ETF flow data |
| `weekly_cot_collection` | Friday at 5:00 PM ET | Collect CFTC Commitment of Traders data |
| `daily_comex_inventory` | Daily at 6:00 PM ET | Collect COMEX warehouse inventory |
| `hourly_google_trends` | Every hour | Collect Google search interest data |
| `reddit_sentiment_collection` | Every 4 hours | Collect Reddit sentiment data |
| `daily_signal_generation` | Daily at 7:00 PM ET | Generate trading signals from all data |

## Basic Usage

### Starting the Scheduler

```python
from app.services.scheduler_service import scheduler_service

# Start the scheduler (schedules all jobs)
scheduler_service.start_scheduler()
```

### Stopping the Scheduler

```python
# Stop gracefully (wait for running jobs to complete)
scheduler_service.stop_scheduler(wait=True)

# Stop immediately
scheduler_service.stop_scheduler(wait=False)
```

### Manually Trigger a Job

```python
# Trigger a specific job manually
result = await scheduler_service.trigger_job('daily_price_collection', triggered_by='API')

print(result)
# {
#     'success': True,
#     'job_name': 'daily_price_collection',
#     'result': {...}
# }
```

### Get Job Execution History

```python
# Get history for a specific job
history = await scheduler_service.get_job_history(
    job_name='daily_price_collection',
    limit=50
)

# Get history for all jobs
all_history = await scheduler_service.get_job_history(limit=100)
```

### List Scheduled Jobs

```python
# Get all scheduled jobs
jobs = scheduler_service.get_scheduled_jobs()

for job in jobs:
    print(f"{job['job_name']}: Next run at {job['next_run_time']}")
```

### Pause/Resume Jobs

```python
# Pause a job
scheduler_service.pause_job('hourly_google_trends')

# Resume a paused job
scheduler_service.resume_job('hourly_google_trends')
```

### Add Custom Job

```python
from apscheduler.triggers.cron import CronTrigger

async def my_custom_job():
    # Your custom logic here
    return {'records_saved': 10}

# Add to scheduler
scheduler_service.add_job(
    job_name='my_custom_job',
    func=scheduler_service._job_wrapper(my_custom_job, 'CUSTOM'),
    trigger=CronTrigger(hour=12, minute=0),
    job_id='my_custom_job',
    name='My Custom Job'
)
```

### Remove a Job

```python
scheduler_service.remove_job('hourly_google_trends')
```

## Integration with FastAPI

### Example API Endpoint

```python
from fastapi import APIRouter, HTTPException
from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

@router.post("/jobs/{job_name}/trigger")
async def trigger_job(job_name: str):
    """Manually trigger a job"""
    result = await scheduler_service.trigger_job(job_name, triggered_by='API')

    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))

    return result

@router.get("/jobs")
async def list_jobs():
    """Get all scheduled jobs"""
    return scheduler_service.get_scheduled_jobs()

@router.get("/jobs/{job_name}/history")
async def get_job_history(job_name: str, limit: int = 50):
    """Get execution history for a job"""
    return await scheduler_service.get_job_history(job_name, limit)

@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a job"""
    success = scheduler_service.pause_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to pause job {job_id}")
    return {"status": "paused", "job_id": job_id}

@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused job"""
    success = scheduler_service.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to resume job {job_id}")
    return {"status": "resumed", "job_id": job_id}
```

## Job Wrapper Features

The `_job_wrapper` function automatically:

1. **Logs execution** - Start and end times, duration, status
2. **Tracks in database** - Creates DataJob records for each execution
3. **Handles errors** - Catches exceptions and logs stack traces
4. **Records metrics** - Tracks records processed, saved, errors
5. **Returns results** - Standardized result format

## Database Schema (data_jobs table)

```sql
CREATE TABLE data_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    records_processed INTEGER DEFAULT 0,
    records_saved INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    triggered_by VARCHAR(50) DEFAULT 'SCHEDULER',
    job_params JSONB,
    result_summary JSONB,
    error_message TEXT,
    error_traceback TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    is_retry BOOLEAN DEFAULT FALSE,
    parent_job_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_data_jobs_job_name ON data_jobs(job_name);
CREATE INDEX idx_data_jobs_started_at ON data_jobs(started_at);
```

## Running the Migration

After creating the model, run the database migration:

```bash
# Create migration
cd backend
alembic revision --autogenerate -m "Add data_jobs table"

# Apply migration
alembic upgrade head
```

## Application Startup

Add to your FastAPI application startup:

```python
from contextlib import asynccontextmanager
from app.services.scheduler_service import scheduler_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting scheduler service...")
    scheduler_service.start_scheduler()

    yield

    # Shutdown
    logger.info("Stopping scheduler service...")
    scheduler_service.stop_scheduler(wait=True)

app = FastAPI(lifespan=lifespan)
```

## Monitoring and Logging

All job executions are logged with Loguru:

```
2025-12-28 17:00:00 | INFO | STARTING JOB: _collect_daily_prices
2025-12-28 17:00:05 | SUCCESS | JOB COMPLETED: _collect_daily_prices
Duration: 5.2s
```

Failed jobs log full stack traces for debugging.

## Error Handling

Jobs automatically handle errors and:
- Log error messages and stack traces
- Update DataJob record with failure status
- Continue running other scheduled jobs
- Can be configured for automatic retries (enhancement needed)

## Best Practices

1. **Monitor job history** - Regularly check `data_jobs` table for failures
2. **Set up alerts** - Alert on job failures using the database records
3. **Review logs** - Check Loguru logs for detailed execution information
4. **Test jobs manually** - Use `trigger_job()` before relying on schedules
5. **Handle timezone** - All times are in Eastern Time (America/New_York)
6. **Avoid overlaps** - Jobs are configured with `max_instances=1`

## Dependencies

Required packages (add to requirements.txt):
```
apscheduler>=3.10.0
```

## Notes

- All times are in **Eastern Time (America/New_York)** for market hours alignment
- Jobs won't overlap (max_instances=1)
- Missed jobs are combined (coalesce=True)
- 5-minute grace period for delayed executions (misfire_grace_time=300)
- Signal generation runs last (7 PM ET) to use all collected data
