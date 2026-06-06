import uuid
from sqlalchemy import Column, String, DateTime, Float, func
from src.backend.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metrics
    ocr_duration_sec = Column(Float, nullable=True)
    llm_duration_sec = Column(Float, nullable=True)
    total_duration_sec = Column(Float, nullable=True)
    
    # S3 paths for inputs and outputs are deterministically formed using the job ID
