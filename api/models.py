# api/models.py

"""Pydantic request/response models for the Pipeline Healer API."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request Models ────────────────────────────────────────────

class HealRequest(BaseModel):
    """Request body for the /heal endpoint."""

    repo_name: str = Field(
        ...,
        description="GitHub repository in 'owner/repo' format",
        examples=["username/my-project"],
        pattern=r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$",
    )
    run_id: str = Field(
        ...,
        description="GitHub Actions workflow run ID",
        examples=["12345678901"],
        pattern=r"^\d+$",
    )


# ── Response Models ───────────────────────────────────────────

class HealResponse(BaseModel):
    """Response from the /heal endpoint."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(default=JobStatus.QUEUED)
    message: str = Field(default="Healing job queued")


class JobStatusResponse(BaseModel):
    """Response from the /status/{job_id} endpoint."""

    job_id: str
    status: JobStatus
    repo_name: str
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_step: str = "queued"
    pr_url: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime


class HistoryItem(BaseModel):
    """A single item in the healing history."""

    job_id: str
    repo_name: str
    run_id: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    pr_url: Optional[str] = None


class HistoryResponse(BaseModel):
    """Response from the /history endpoint."""

    total: int
    jobs: list[HistoryItem]
