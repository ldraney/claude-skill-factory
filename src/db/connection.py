"""
Database Connection

Async database operations for batch tracking.
"""
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update

from src.db.models import Base, BatchJob, BatchItem, BatchStatus

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://factory:factory_dev@localhost:5432/skill_factory")

# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_batch_job(batch_id: str, skill_name: str, total_items: int) -> BatchJob:
    """Create a new batch job record."""
    async with async_session() as session:
        job = BatchJob(
            id=batch_id,
            skill_name=skill_name,
            status=BatchStatus.PROCESSING.value,
            total_items=total_items
        )
        session.add(job)
        await session.commit()
        return job


async def create_batch_item(batch_id: str, item_id: str, input_data: dict) -> BatchItem:
    """Create a batch item record."""
    async with async_session() as session:
        item = BatchItem(
            id=item_id,
            batch_id=batch_id,
            input_data=input_data
        )
        session.add(item)
        await session.commit()
        return item


async def update_batch_item(
    batch_id: str,
    item_id: str,
    success: bool,
    output: dict | None,
    error_type: str | None,
    error_message: str | None,
    tokens_used: int,
    latency_ms: int
):
    """Update a batch item with results."""
    async with async_session() as session:
        stmt = update(BatchItem).where(BatchItem.id == item_id).values(
            success=success,
            output_data=output,
            error_type=error_type,
            error_message=error_message,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            processed_at=datetime.utcnow()
        )
        await session.execute(stmt)
        
        # Update batch job counters
        if success:
            stmt = update(BatchJob).where(BatchJob.id == batch_id).values(
                completed_items=BatchJob.completed_items + 1
            )
        else:
            stmt = update(BatchJob).where(BatchJob.id == batch_id).values(
                failed_items=BatchJob.failed_items + 1
            )
        await session.execute(stmt)
        
        # Check if batch is complete
        result = await session.execute(
            select(BatchJob).where(BatchJob.id == batch_id)
        )
        job = result.scalar_one_or_none()
        
        if job and (job.completed_items + job.failed_items) >= job.total_items:
            stmt = update(BatchJob).where(BatchJob.id == batch_id).values(
                status=BatchStatus.COMPLETED.value
            )
            await session.execute(stmt)
        
        await session.commit()


async def update_batch_job_status(batch_id: str, status: BatchStatus):
    """Update batch job status."""
    async with async_session() as session:
        stmt = update(BatchJob).where(BatchJob.id == batch_id).values(status=status.value)
        await session.execute(stmt)
        await session.commit()


async def get_batch_status(batch_id: str) -> dict | None:
    """Get batch job status."""
    async with async_session() as session:
        result = await session.execute(
            select(BatchJob).where(BatchJob.id == batch_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        return {
            "status": job.status,
            "total": job.total_items,
            "completed": job.completed_items,
            "failed": job.failed_items,
            "created_at": job.created_at.isoformat() if job.created_at else None
        }


async def get_batch_results(batch_id: str) -> list[dict]:
    """Get all results for a batch."""
    async with async_session() as session:
        result = await session.execute(
            select(BatchItem).where(BatchItem.batch_id == batch_id)
        )
        items = result.scalars().all()
        
        return [
            {
                "item_id": item.id,
                "input": item.input_data,
                "output": item.output_data,
                "success": item.success,
                "error_type": item.error_type,
                "error_message": item.error_message,
                "tokens_used": item.tokens_used,
                "latency_ms": item.latency_ms
            }
            for item in items
        ]
