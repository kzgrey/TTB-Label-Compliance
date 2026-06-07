import os
from celery import Celery, chord
from src.backend.config import settings
from src.backend.database import SessionLocal
from src.backend.models import Job
from src.backend.services.s3 import download_job_input, upload_job_output
from src.backend.services.ocr import process_image_with_tesseract
from src.backend.services.llm import get_llm_provider

celery_app = Celery(
    "job_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# @celery_app.task
# def task_ocr(job_id: str, file_key: str):
#     file_bytes = download_job_input(file_key)
#     result = process_image_with_tesseract(file_bytes)
#     return {"job_id": job_id, "ocr_result": result}

# @celery_app.task
# def task_llm(job_id: str, file_key: str, prompt: str):
#     file_bytes = download_job_input(file_key)
#     provider = get_llm_provider()
#     result = provider.execute_prompt(prompt, file_bytes)
#     return {"job_id": job_id, "llm_result": result}

@celery_app.task
def task_join_results(results: list, job_id: str):
    # results will contain the dicts from task_ocr and task_llm
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        db.close()
        return
        
    final_output = {}
    ocr_duration = 0.0
    llm_duration = 0.0

    for res in results:
        if "ocr_result" in res:
            final_output["ocr"] = res["ocr_result"]["text"]
            ocr_duration = res["ocr_result"]["duration_sec"]
        elif "llm_result" in res:
            final_output["llm"] = res["llm_result"]["output"]["text"] if isinstance(res["llm_result"].get("output"), dict) else res["llm_result"].get("text", "")
            if not final_output["llm"] and "output" in res["llm_result"]:
                final_output["llm"] = res["llm_result"]["output"]
            llm_duration = res["llm_result"]["duration_sec"]

    # Upload final output to S3
    upload_job_output(job_id, final_output)
    
    # Update Job in DB
    job.status = "completed"
    job.ocr_duration_sec = ocr_duration
    job.llm_duration_sec = llm_duration
    job.total_duration_sec = ocr_duration + llm_duration  # rough sum, or we can compute real total
    db.commit()
    db.close()
    
    return final_output

@celery_app.task
def task_error_handler(request, exc, traceback, job_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = "failed"
        db.commit()
    db.close()

def start_job_pipeline(job_id: str, file_key: str, prompt: str):
    """
    Kicks off the Celery chord.
    """
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = "processing"
        db.commit()
    db.close()

    # Create a chord: run OCR and LLM in parallel, then join
    callback = task_join_results.s(job_id=job_id).on_error(task_error_handler.s(job_id=job_id))
    header = [
        task_ocr.s(job_id, file_key),
        task_llm.s(job_id, file_key, prompt)
    ]
    chord(header)(callback)

@celery_app.task
def execute_job_task(job_type: str, job_id: str, *args, **kwargs):
    """
    Celery task wrapper to execute standard Python class jobs.
    """
    if job_type == "AnalyzeLabelJob":
        from src.backend.jobs.analyze_label import AnalyzeLabelJob
        job = AnalyzeLabelJob(job_id)
        return job.execute(*args, **kwargs)
    else:
        raise ValueError(f"Unknown job type: {job_type}")
