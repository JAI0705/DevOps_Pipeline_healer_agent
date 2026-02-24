# api/server.py

"""
FastAPI application for the Pipeline Healer Agent.

Provides REST endpoints for triggering healing, checking status,
and viewing history.

Usage:
    uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
"""

import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException

load_dotenv()

from agent.graph import healing_graph
from api.models import (
    HealRequest,
    HealResponse,
    HealthResponse,
    HistoryItem,
    HistoryResponse,
    JobStatus,
    JobStatusResponse,
)
from utils.logger import get_logger

logger = get_logger("api.server")

# ── In-memory job store (use Redis/DB in production) ─────────
_jobs: dict[str, dict] = {}

# ── FastAPI App ───────────────────────────────────────────────

app = FastAPI(
    title="Pipeline Healer API",
    description=(
        "AI-powered agent that automatically detects, analyzes, and fixes "
        "failed GitHub Actions pipelines."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register webhook router (imported after app creation to avoid circular imports)
from api.webhooks import router as webhook_router

app.include_router(webhook_router)


# ── Background task ──────────────────────────────────────────

def _run_healing(job_id: str, repo_name: str, run_id: str):
    """Execute the healing workflow as a background task."""
    _jobs[job_id]["status"] = JobStatus.RUNNING
    _jobs[job_id]["current_step"] = "starting"

    initial_state = {
        "repo_name": repo_name,
        "run_id": run_id,
        "error_logs": "",
        "failed_file": "",
        "error_analysis": "",
        "proposed_fix": "",
        "fix_explanation": "",
        "branch_name": "",
        "pr_url": None,
        "current_step": "starting",
        "success": False,
    }

    try:
        final_state = healing_graph.invoke(initial_state)

        _jobs[job_id].update({
            "status": JobStatus.COMPLETED,
            "completed_at": datetime.now(timezone.utc),
            "current_step": final_state.get("current_step", "completed"),
            "pr_url": final_state.get("pr_url"),
        })

        logger.info(f"Job {job_id} completed — PR: {final_state.get('pr_url')}")

    except Exception as e:
        _jobs[job_id].update({
            "status": JobStatus.FAILED,
            "completed_at": datetime.now(timezone.utc),
            "current_step": "failed",
            "error": str(e),
        })
        logger.error(f"Job {job_id} failed: {e}")


# ── Endpoints ─────────────────────────────────────────────────

@app.post("/heal", response_model=HealResponse, status_code=202)
async def heal_pipeline(request: HealRequest, background_tasks: BackgroundTasks):
    """
    Trigger a healing workflow for a failed pipeline.

    The healing runs asynchronously — use `/status/{job_id}` to check progress.
    """
    job_id = str(uuid.uuid4())[:8]

    _jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "repo_name": request.repo_name,
        "run_id": request.run_id,
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "current_step": "queued",
        "pr_url": None,
        "error": None,
    }

    background_tasks.add_task(_run_healing, job_id, request.repo_name, request.run_id)

    logger.info(f"Healing job {job_id} queued for {request.repo_name} run {request.run_id}")

    return HealResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message=f"Healing job queued for {request.repo_name}",
    )


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Check the status of a healing job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    job = _jobs[job_id]
    return JobStatusResponse(**job)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/history", response_model=HistoryResponse)
async def get_history(limit: int = 20):
    """Get recent healing job history."""
    items = sorted(
        _jobs.values(),
        key=lambda j: j["started_at"],
        reverse=True,
    )[:limit]

    return HistoryResponse(
        total=len(_jobs),
        jobs=[
            HistoryItem(
                job_id=j["job_id"],
                repo_name=j["repo_name"],
                run_id=j["run_id"],
                status=j["status"],
                started_at=j["started_at"],
                completed_at=j.get("completed_at"),
                pr_url=j.get("pr_url"),
            )
            for j in items
        ],
    )
