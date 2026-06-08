import io
from fastapi import FastAPI, UploadFile, Form, File, Depends, HTTPException
from fastapi.responses import Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import redis
from typing import List, Optional

from src.backend.config import settings
from src.backend.database import engine, Base, get_db
from src.backend.models import Job
from src.backend.services.s3 import upload_job_input, upload_job_prompt, get_job_data, get_presigned_image_url
from src.backend.worker import execute_job_task

app = FastAPI(title="Job Processing API")

redis_client = redis.Redis.from_url(settings.REDIS_URL)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
Base.metadata.create_all(bind=engine)

@app.get("/")
def health_check():
    """Health check endpoint for AWS ALB."""
    return {"status": "ok"}

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
async def submit_job(
    prompt: str = Form(""), 
    use_llm_ocr: bool = Form(False),
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Submits a new job.
    1. Saves the file to a unique S3 key.
    2. Enqueues a Celery task.
    3. Returns the job ID.
    """
    job = Job(status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Save to S3 and cache in Redis (1 hour TTL)
    file_bytes = await file.read()
    redis_client.setex(f"image:{job.id}", 3600, file_bytes)
    file_key = upload_job_input(str(job.id), file_bytes, "image.png")

    # Save prompt to S3 for history
    upload_job_prompt(job.id, prompt)

    # Submit Celery Task
    execute_job_task.delay("AnalyzeLabelJob", job.id, file_key=file_key, prompt=prompt, use_llm_ocr=use_llm_ocr)
    
    return {"message": "Job submitted successfully", "job_id": job.id}

@app.get("/jobs/{job_id}/details")
def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """
    Returns the job details including S3 data (LLM/OCR outputs and prompt).
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    data = get_job_data(job_id)
    return {
        "job": {
            "id": job.id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "ocr_duration_sec": job.ocr_duration_sec,
            "llm_duration_sec": job.llm_duration_sec,
            "total_duration_sec": job.total_duration_sec
        },
        "prompt": data.get("prompt"),
        "output": data.get("output")
    }

@app.get("/jobs/{job_id}/image")
def get_job_image(job_id: str, db: Session = Depends(get_db)):
    """
    Returns the raw image from Redis if cached, otherwise redirects to the S3 presigned URL.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    cached_img = redis_client.get(f"image:{job_id}")
    if cached_img:
        return Response(content=cached_img, media_type="image/png")
        
    url = get_presigned_image_url(job_id, "image.png")
    return RedirectResponse(url=url)
