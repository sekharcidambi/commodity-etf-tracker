"""Scheduler control endpoints - Manage automated data collection jobs"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.services.scheduler_service import scheduler_service

router = APIRouter()


# ============================================================================
# SCHEDULER STATUS
# ============================================================================

@router.get("/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    Get current scheduler status

    Returns:
    - running: Whether scheduler is active
    - jobs_count: Number of scheduled jobs
    - timestamp: Current timestamp
    """
    try:
        jobs = scheduler_service.get_scheduled_jobs()

        # Count paused vs active jobs
        active_jobs = [j for j in jobs if not j.get('is_paused', False)]
        paused_jobs = [j for j in jobs if j.get('is_paused', False)]

        return {
            "running": scheduler_service.is_running,
            "jobs_count": len(jobs),
            "active_jobs": len(active_jobs),
            "paused_jobs": len(paused_jobs),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# JOB LISTING AND DETAILS
# ============================================================================

@router.get("/jobs")
async def list_scheduled_jobs() -> Dict[str, Any]:
    """
    List all scheduled jobs with next run times

    Returns:
    - jobs: List of all scheduled jobs
    - Each job includes:
      - job_id: Unique job identifier
      - job_name: Human-readable name
      - next_run_time: Next scheduled execution (ISO format)
      - trigger: Trigger configuration (cron/interval)
      - is_paused: Whether job is currently paused
    """
    try:
        jobs = scheduler_service.get_scheduled_jobs()

        if not jobs:
            logger.warning("No scheduled jobs found")
            return {
                "jobs_count": 0,
                "jobs": [],
                "note": "No jobs currently scheduled"
            }

        # Sort by next_run_time (soonest first)
        jobs_sorted = sorted(
            jobs,
            key=lambda x: x.get('next_run_time') or '9999-12-31',
            reverse=False
        )

        return {
            "jobs_count": len(jobs_sorted),
            "jobs": jobs_sorted,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_name}/history")
async def get_job_execution_history(
    job_name: str,
    limit: int = Query(50, ge=1, le=500, description="Number of history records to retrieve")
) -> Dict[str, Any]:
    """
    Get execution history for a specific job

    Args:
    - job_name: Name of the job to query
    - limit: Maximum number of records to return (1-500, default: 50)

    Returns:
    - history: List of job execution records
    - Each record includes:
      - id: Execution record ID
      - status: RUNNING, COMPLETED, or FAILED
      - started_at: Start timestamp
      - completed_at: Completion timestamp
      - duration_seconds: Execution duration
      - records_processed: Number of records processed
      - error_message: Error details (if failed)
    """
    try:
        logger.info(f"Fetching execution history for job: {job_name}")

        history = await scheduler_service.get_job_history(
            job_name=job_name,
            limit=limit
        )

        if not history:
            logger.warning(f"No history found for job: {job_name}")
            return {
                "job_name": job_name,
                "executions_count": 0,
                "history": [],
                "note": f"No execution history found for {job_name}"
            }

        # Calculate statistics
        completed = [h for h in history if h['status'] == 'COMPLETED']
        failed = [h for h in history if h['status'] == 'FAILED']

        stats = {
            "total_executions": len(history),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": round(len(completed) / len(history) * 100, 2) if history else 0
        }

        # Calculate average duration for completed jobs
        if completed:
            durations = [h['duration_seconds'] for h in completed if h['duration_seconds']]
            if durations:
                stats['avg_duration_seconds'] = round(sum(durations) / len(durations), 2)

        return {
            "job_name": job_name,
            "executions_count": len(history),
            "statistics": stats,
            "history": history,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching job history for {job_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# JOB CONTROL - TRIGGER
# ============================================================================

@router.post("/jobs/{job_name}/trigger")
async def trigger_job_manually(
    job_name: str,
    triggered_by: str = Query("API", description="Who/what triggered this execution")
) -> Dict[str, Any]:
    """
    Manually trigger a job execution

    Args:
    - job_name: Name of the job to trigger
    - triggered_by: Identifier for who/what triggered the job (default: API)

    Available jobs:
    - daily_price_collection
    - weekly_flow_collection
    - weekly_cot_collection
    - daily_comex_inventory
    - hourly_google_trends
    - reddit_sentiment_collection
    - daily_signal_generation

    Returns:
    - success: Whether execution started successfully
    - job_name: Name of triggered job
    - triggered_at: Timestamp when job was triggered
    - result: Execution result (if completed synchronously)
    """
    try:
        logger.info(f"Manual trigger request for job: {job_name} by {triggered_by}")

        if not scheduler_service.is_running:
            logger.warning("Scheduler is not running")
            raise HTTPException(
                status_code=503,
                detail="Scheduler service is not running"
            )

        # Trigger the job
        result = await scheduler_service.trigger_job(
            job_name=job_name,
            triggered_by=triggered_by
        )

        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Failed to trigger job {job_name}: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to trigger job: {error_msg}"
            )

        logger.success(f"Successfully triggered job: {job_name}")

        return {
            "success": True,
            "job_name": job_name,
            "triggered_by": triggered_by,
            "triggered_at": datetime.utcnow().isoformat(),
            "result": result.get('result')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering job {job_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# JOB CONTROL - PAUSE/RESUME
# ============================================================================

@router.post("/jobs/{job_id}/pause")
async def pause_scheduled_job(job_id: str) -> Dict[str, Any]:
    """
    Pause a scheduled job

    Args:
    - job_id: ID of the job to pause

    Effect:
    - Job will not execute on schedule until resumed
    - Job can still be triggered manually

    Returns:
    - success: Whether pause was successful
    - job_id: ID of paused job
    - status: Current job status
    """
    try:
        logger.info(f"Pause request for job: {job_id}")

        if not scheduler_service.is_running:
            logger.warning("Scheduler is not running")
            raise HTTPException(
                status_code=503,
                detail="Scheduler service is not running"
            )

        # Pause the job
        success = scheduler_service.pause_job(job_id)

        if not success:
            logger.error(f"Failed to pause job: {job_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to pause job {job_id}. Job may not exist."
            )

        logger.success(f"Successfully paused job: {job_id}")

        return {
            "success": True,
            "job_id": job_id,
            "status": "PAUSED",
            "paused_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/resume")
async def resume_scheduled_job(job_id: str) -> Dict[str, Any]:
    """
    Resume a paused job

    Args:
    - job_id: ID of the job to resume

    Effect:
    - Job will resume normal scheduled execution
    - Next run time will be calculated based on trigger

    Returns:
    - success: Whether resume was successful
    - job_id: ID of resumed job
    - status: Current job status
    - next_run_time: When job will next execute
    """
    try:
        logger.info(f"Resume request for job: {job_id}")

        if not scheduler_service.is_running:
            logger.warning("Scheduler is not running")
            raise HTTPException(
                status_code=503,
                detail="Scheduler service is not running"
            )

        # Resume the job
        success = scheduler_service.resume_job(job_id)

        if not success:
            logger.error(f"Failed to resume job: {job_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to resume job {job_id}. Job may not exist."
            )

        # Get updated job info to return next_run_time
        jobs = scheduler_service.get_scheduled_jobs()
        resumed_job = next((j for j in jobs if j['job_id'] == job_id), None)

        next_run = resumed_job.get('next_run_time') if resumed_job else None

        logger.success(f"Successfully resumed job: {job_id}")

        return {
            "success": True,
            "job_id": job_id,
            "status": "ACTIVE",
            "resumed_at": datetime.utcnow().isoformat(),
            "next_run_time": next_run
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
