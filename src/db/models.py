"""
Database Models

SQLAlchemy models for batch jobs and results.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from datetime import datetime

Base = declarative_base()


class BatchStatus(str, PyEnum):
    """Batch job status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchJob(Base):
    """A batch processing job."""
    __tablename__ = "batch_jobs"
    
    id = Column(String, primary_key=True)
    skill_name = Column(String, nullable=False)
    status = Column(String, default=BatchStatus.QUEUED.value)
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    items = relationship("BatchItem", back_populates="job")


class BatchItem(Base):
    """A single item within a batch."""
    __tablename__ = "batch_items"
    
    id = Column(String, primary_key=True)
    batch_id = Column(String, ForeignKey("batch_jobs.id"), nullable=False)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    success = Column(Boolean, nullable=True)
    error_type = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    job = relationship("BatchJob", back_populates="items")
