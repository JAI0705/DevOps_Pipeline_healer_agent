# api/webhooks.py

"""
GitHub webhook handler for automatic pipeline healing.

Receives `workflow_run` events from GitHub and auto-triggers healing
when a workflow fails.

Setup:
  1. Go to your repo → Settings → Webhooks → Add webhook
  2. Payload URL: https://your-server/webhook/github
  3. Content type: application/json
  4. Secret: set a webhook secret
  5. Events: select "Workflow runs"
"""

import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request

from api.models import HealResponse, JobStatus
from utils.logger import get_logger

logger = get_logger("api.webhooks")

router = APIRouter(prefix="/webhook", tags=["webhooks"])

# Webhook secret for signature verification
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify the GitHub webhook signature (HMAC-SHA256).

    GitHub sends the signature in the X-Hub-Signature-256 header.
    """
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/github", response_model=HealResponse)
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
):
    """
    Receive GitHub webhook events and trigger healing on workflow failures.

    Expected event: `workflow_run` with action `completed` and conclusion `failure`.
    """
    payload = await request.body()

    # Verify webhook signature
    if WEBHOOK_SECRET and not _verify_signature(payload, x_hub_signature_256, WEBHOOK_SECRET):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Only process workflow_run events
    if x_github_event != "workflow_run":
        logger.debug(f"Ignoring event type: {x_github_event}")
        return HealResponse(
            job_id="ignored",
            status=JobStatus.COMPLETED,
            message=f"Event type '{x_github_event}' ignored",
        )

    data = await request.json()
    action = data.get("action", "")
    conclusion = data.get("workflow_run", {}).get("conclusion", "")

    # Only trigger on completed + failed runs
    if action != "completed" or conclusion != "failure":
        logger.debug(f"Ignoring workflow_run: action={action}, conclusion={conclusion}")
        return HealResponse(
            job_id="skipped",
            status=JobStatus.COMPLETED,
            message=f"Workflow run not a failure (action={action}, conclusion={conclusion})",
        )

    # Extract repo and run info
    workflow_run = data["workflow_run"]
    repo_full_name = data["repository"]["full_name"]
    run_id = str(workflow_run["id"])

    logger.info(
        f"Webhook received: failed workflow run {run_id} in {repo_full_name}",
        extra={"step": "webhook"},
    )

    # Trigger healing via the server module
    from api.server import _jobs, _run_healing

    import uuid
    job_id = str(uuid.uuid4())[:8]

    _jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "repo_name": repo_full_name,
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "current_step": "queued",
        "pr_url": None,
        "error": None,
    }

    # Run in background (note: in production, use a proper task queue)
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_healing, job_id, repo_full_name, run_id)

    return HealResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message=f"Auto-healing triggered for {repo_full_name} run {run_id}",
    )
