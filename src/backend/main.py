import io
from fastapi import FastAPI, UploadFile, Form, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from src.backend.database import engine, Base, get_db
from src.backend.models import Job
from src.backend.services.s3 import upload_job_input
from src.backend.worker import start_job_pipeline

app = FastAPI(title="Job Processing API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
Base.metadata.create_all(bind=engine)

class JobResponse(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: Optional[str]
    ocr_duration_sec: Optional[float]
    llm_duration_sec: Optional[float]
    total_duration_sec: Optional[float]

    class Config:
        orm_mode = True

@app.get("/jobs", response_model=List[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    """
    Returns the status of all known jobs in descending order by created timestamp.
    """
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    # Convert datetimes to string for pydantic if necessary, or let it handle
    result = []
    for j in jobs:
        result.append(JobResponse(
            id=j.id,
            status=j.status,
            created_at=j.created_at.isoformat() if j.created_at else "",
            updated_at=j.updated_at.isoformat() if j.updated_at else None,
            ocr_duration_sec=j.ocr_duration_sec,
            llm_duration_sec=j.llm_duration_sec,
            total_duration_sec=j.total_duration_sec
        ))
    return result

@app.post("/jobs/submit")
async def submit_job(prompt: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Submits a new job.
    """
    # Create job in DB
    job = Job(status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Read file
    file_bytes = await file.read()
    
    # Upload to S3
    file_key = upload_job_input(job.id, file_bytes, file.filename)
    
    # Start pipeline
    start_job_pipeline(job.id, file_key, prompt)
    
    return {"message": "Job submitted successfully", "job_id": job.id}
