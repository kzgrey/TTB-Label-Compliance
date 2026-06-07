import logging
import io
import json
from src.backend.services.s3 import get_s3_client, _get_bucket_and_prefix
from src.backend.database import SessionLocal
from src.backend.models import Job

class BaseJob:
    """
    Standard Python class framework for defining extensible jobs.
    """
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{job_id}")
        self.logger.setLevel(logging.INFO)
        
        # Setup string buffer for logging to upload later
        self.log_stream = io.StringIO()
        handler = logging.StreamHandler(self.log_stream)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def upload_file(self, filename: str, content: bytes):
        """Uploads a file to the job's S3 directory automatically."""
        try:
            s3 = get_s3_client()
            bucket, prefix = _get_bucket_and_prefix()
            key = f"{prefix}/{self.job_id}/{filename}" if prefix else f"{self.job_id}/{filename}"
            self.logger.debug(f"BaseJob uploading to S3 - Bucket: {bucket}, Key: {key}")
            s3.put_object(Bucket=bucket, Key=key, Body=content)
            self.logger.debug(f"BaseJob successfully uploaded {key}")
            return key
        except Exception as e:
            self.logger.error(f"BaseJob failed to upload file to S3: {e}", exc_info=True)
            # Log to root logger as well in case the job logger is not working
            logging.getLogger().error(f"BaseJob failed to upload file to S3: {e}", exc_info=True)
            raise

    def initialize(self, *args, **kwargs):
        """Called prior to run(). Subclasses should override this."""
        pass

    def run(self, *args, **kwargs):
        """
        Execute the job logic. Subclasses must implement this method.
        Should contain the full end-to-end lifetime of the job execution.
        """
        raise NotImplementedError("Subclasses must implement run()")

    def cleanup(self):
        """Called after run() completes. Subclasses should override this."""
        pass

    def execute(self, *args, **kwargs):
        """
        Framework orchestrator. Manages state, S3 outputs, logging, and error handling.
        """
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == self.job_id).first()
        if job:
            job.status = "processing"
            db.commit()
        db.close()
        
        try:
            self.logger.info("Initializing job.")
            self.initialize(*args, **kwargs)
            
            self.logger.info("Running job.")
            result = self.run(*args, **kwargs)
            
            self.logger.info("Job completed successfully.")
            
            # Framework automatically saves the returned dict as output.json
            if isinstance(result, dict):
                self.upload_file("output.json", json.dumps(result).encode('utf-8'))
                
            db = SessionLocal()
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.status = "completed"
                if isinstance(result, dict):
                    job.ocr_duration_sec = result.get("ocr_duration_sec", 0.0)
                    job.llm_duration_sec = result.get("llm_duration_sec", 0.0)
                    job.total_duration_sec = result.get("total_duration_sec", 0.0)
                db.commit()
            db.close()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Job failed: {str(e)}", exc_info=True)
            db = SessionLocal()
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.status = "failed"
                db.commit()
            db.close()
            raise
            
        finally:
            self.logger.info("Cleaning up job.")
            try:
                self.cleanup()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
                
            # Upload captured logs
            log_content = self.log_stream.getvalue().encode('utf-8')
            self.upload_file("log.txt", log_content)
