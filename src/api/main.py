"""
Claude Skill Factory API

The operator interface for submitting batches and querying results.
"""
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import csv
import io
import uuid

from src.queue.tasks import process_skill_batch
from src.db.models import BatchJob, BatchStatus

app = FastAPI(
    title="Claude Skill Factory",
    description="Industrial-grade pipeline for processing data through Claude skills",
    version="0.1.0"
)


class BatchSubmission(BaseModel):
    """Request to process a batch through a skill."""
    skill_name: str
    inputs: list[dict]
    webhook_url: Optional[str] = None


class BatchResponse(BaseModel):
    """Response after batch submission."""
    batch_id: str
    status: str
    item_count: int
    message: str


@app.get("/")
async def root():
    return {
        "service": "Claude Skill Factory",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/skills")
async def list_skills():
    """List all available skills."""
    from src.skills.registry import SKILL_REGISTRY
    return {
        "skills": [
            {
                "name": name,
                "description": skill.description,
                "input_schema": skill.input_schema.model_json_schema(),
                "output_schema": skill.output_schema.model_json_schema()
            }
            for name, skill in SKILL_REGISTRY.items()
        ]
    }


@app.post("/batch", response_model=BatchResponse)
async def submit_batch(submission: BatchSubmission):
    """
    Submit a batch of inputs to be processed by a skill.
    
    Returns a batch_id for tracking progress.
    """
    from src.skills.registry import SKILL_REGISTRY
    
    if submission.skill_name not in SKILL_REGISTRY:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown skill: {submission.skill_name}. Use GET /skills to list available skills."
        )
    
    batch_id = str(uuid.uuid4())
    
    # Queue the batch for processing
    process_skill_batch.delay(
        batch_id=batch_id,
        skill_name=submission.skill_name,
        inputs=submission.inputs,
        webhook_url=submission.webhook_url
    )
    
    return BatchResponse(
        batch_id=batch_id,
        status="queued",
        item_count=len(submission.inputs),
        message=f"Batch queued for processing with skill '{submission.skill_name}'"
    )


@app.post("/batch/csv/{skill_name}", response_model=BatchResponse)
async def submit_csv_batch(skill_name: str, file: UploadFile):
    """
    Submit a CSV file as a batch. Each row becomes one input.
    
    CSV headers become input field names.
    """
    from src.skills.registry import SKILL_REGISTRY
    
    if skill_name not in SKILL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown skill: {skill_name}")
    
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
    inputs = list(reader)
    
    if not inputs:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    
    batch_id = str(uuid.uuid4())
    
    process_skill_batch.delay(
        batch_id=batch_id,
        skill_name=skill_name,
        inputs=inputs,
        webhook_url=None
    )
    
    return BatchResponse(
        batch_id=batch_id,
        status="queued",
        item_count=len(inputs),
        message=f"CSV batch queued ({len(inputs)} rows) for skill '{skill_name}'"
    )


@app.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get the status and results of a batch job."""
    from src.db.connection import get_batch_status, get_batch_results
    
    status = await get_batch_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    response = {
        "batch_id": batch_id,
        "status": status["status"],
        "total": status["total"],
        "completed": status["completed"],
        "failed": status["failed"],
        "created_at": status["created_at"],
    }
    
    if status["status"] == "completed":
        response["results"] = await get_batch_results(batch_id)
    
    return response


@app.get("/health")
async def health_check():
    """Health check for container orchestration."""
    return {"status": "healthy"}
