from src.backend.jobs.base import BaseJob
from src.backend.services.s3 import get_s3_client, _get_bucket_and_prefix

class AnalyzeLabelJob(BaseJob):
    """
    Analyzes a TTB label application. Currently, it just instantiates a logger
    and uploads a log message to S3.
    """
    def run(self, *args, **kwargs):
        self.logger.info(f"AnalyzeLabelJob started for job_id: {self.job_id}")
        
        log_message = f"AnalyzeLabelJob running for job_id: {self.job_id}\n"
        
        s3 = get_s3_client()
        bucket, prefix = _get_bucket_and_prefix()
        
        # Upload to s3://${bucket from env}/jobs/${jobid}/log.txt
        # Ensuring prefix is respected if it exists, otherwise defaulting to 'jobs/'
        key = f"jobs/{self.job_id}/log.txt"
        if prefix and prefix != "/":
            # If a non-root prefix is defined, nest it. But per user comment "just make the prefix /"
            # we assume the base path is standard without complex prefixing.
            pass
            
        s3.put_object(Bucket=bucket, Key=key, Body=log_message.encode('utf-8'))
        
        return {"status": "completed", "job_id": self.job_id}
