"""
Celery Tasks

Batch processing tasks with rate limiting and error handling.
"""
import asyncio
from celery import group
from src.queue.celery_app import celery_app
from src.skills.registry import get_skill
from src.db.connection import (
    create_batch_job, 
    create_batch_item,
    update_batch_item,
    update_batch_job_status
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_skill_batch(self, batch_id: str, skill_name: str, inputs: list[dict], webhook_url: str | None = None):
    """
    Process a batch of inputs through a skill.
    
    Creates individual tasks for each item, tracks progress.
    """
    skill = get_skill(skill_name)
    if not skill:
        raise ValueError(f"Unknown skill: {skill_name}")
    
    # Run async setup in sync context
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_batch_job(batch_id, skill_name, len(inputs)))
    
    # Queue individual items
    tasks = []
    for i, input_data in enumerate(inputs):
        item_id = f"{batch_id}:{i}"
        loop.run_until_complete(create_batch_item(batch_id, item_id, input_data))
        tasks.append(process_single_item.s(batch_id, item_id, skill_name, input_data))
    
    # Execute all items (Celery will handle rate limiting)
    job = group(tasks)
    result = job.apply_async()
    
    # Optional: webhook notification when complete
    if webhook_url:
        notify_completion.apply_async(
            args=[batch_id, webhook_url],
            countdown=10  # Check after initial burst
        )
    
    return {"batch_id": batch_id, "items_queued": len(inputs)}


@celery_app.task(bind=True, max_retries=5, rate_limit="10/s")
def process_single_item(self, batch_id: str, item_id: str, skill_name: str, input_data: dict):
    """
    Process a single item through a skill.
    
    Handles retries for rate limits and transient failures.
    """
    from src.skills.base import SkillErrorType
    
    skill = get_skill(skill_name)
    if not skill:
        raise ValueError(f"Unknown skill: {skill_name}")
    
    # Run the skill
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(skill.run(input_data))
    
    # Handle retryable errors
    if not result.success and result.error_type == SkillErrorType.RATE_LIMIT:
        raise self.retry(exc=Exception("Rate limited"), countdown=30 * (self.request.retries + 1))
    
    if not result.success and result.error_type == SkillErrorType.API_ERROR:
        raise self.retry(exc=Exception(result.error_message), countdown=10)
    
    # Store result
    loop.run_until_complete(update_batch_item(
        batch_id=batch_id,
        item_id=item_id,
        success=result.success,
        output=result.output,
        error_type=result.error_type.value if result.error_type else None,
        error_message=result.error_message,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms
    ))
    
    return {
        "item_id": item_id,
        "success": result.success,
        "error_type": result.error_type.value if result.error_type else None
    }


@celery_app.task
def notify_completion(batch_id: str, webhook_url: str):
    """Send webhook notification when batch completes."""
    import httpx
    
    loop = asyncio.get_event_loop()
    
    # Check if batch is complete
    from src.db.connection import get_batch_status
    status = loop.run_until_complete(get_batch_status(batch_id))
    
    if status and status["status"] == "completed":
        # Send webhook
        try:
            with httpx.Client() as client:
                client.post(webhook_url, json={
                    "batch_id": batch_id,
                    "status": "completed",
                    "total": status["total"],
                    "completed": status["completed"],
                    "failed": status["failed"]
                })
        except Exception as e:
            print(f"Webhook notification failed: {e}")
    else:
        # Recheck in 30 seconds
        notify_completion.apply_async(args=[batch_id, webhook_url], countdown=30)
