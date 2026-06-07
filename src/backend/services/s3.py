import json
import boto3
from botocore.config import Config
from src.backend.config import settings

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION,
        config=Config(signature_version='s3v4')
    )

def _get_bucket_and_prefix():
    parts = settings.S3_BUCKET_PATH.strip('/').split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket, prefix

def upload_job_input(job_id: str, file_bytes: bytes, filename: str):
    s3 = get_s3_client()
    bucket, prefix = _get_bucket_and_prefix()
    key = f"{prefix}/{job_id}/input/{filename}" if prefix else f"{job_id}/input/{filename}"
    s3.put_object(Bucket=bucket, Key=key, Body=file_bytes)
    return key

def download_job_input(key: str) -> bytes:
    s3 = get_s3_client()
    bucket, _ = _get_bucket_and_prefix()
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()

def upload_job_output(job_id: str, data: dict):
    s3 = get_s3_client()
    bucket, prefix = _get_bucket_and_prefix()
    key = f"{prefix}/{job_id}/output.json" if prefix else f"{job_id}/output.json"
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(data).encode('utf-8'))
    return key

def upload_job_prompt(job_id: str, prompt: str):
    s3 = get_s3_client()
    bucket, prefix = _get_bucket_and_prefix()
    key = f"{prefix}/{job_id}/input/prompt.txt" if prefix else f"{job_id}/input/prompt.txt"
    s3.put_object(Bucket=bucket, Key=key, Body=prompt.encode('utf-8'))
    return key

def get_job_data(job_id: str) -> dict:
    s3 = get_s3_client()
    bucket, prefix = _get_bucket_and_prefix()
    
    prompt_key = f"{prefix}/{job_id}/input/prompt.txt" if prefix else f"{job_id}/input/prompt.txt"
    output_key = f"{prefix}/{job_id}/output.json" if prefix else f"{job_id}/output.json"
    
    result = {"prompt": None, "output": None}
    
    try:
        prompt_resp = s3.get_object(Bucket=bucket, Key=prompt_key)
        result["prompt"] = prompt_resp['Body'].read().decode('utf-8')
    except Exception:
        pass
        
    try:
        output_resp = s3.get_object(Bucket=bucket, Key=output_key)
        result["output"] = json.loads(output_resp['Body'].read().decode('utf-8'))
    except Exception:
        pass
        
    return result

