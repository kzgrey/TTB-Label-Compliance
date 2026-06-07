import json
import boto3
import logging
from botocore.config import Config
from src.backend.config import settings

logger = logging.getLogger("s3_operations")
logger.setLevel(logging.DEBUG)
# Add a console handler to ensure S3 logs are printed to stdout
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

def get_s3_client():
    return boto3.client(
        's3',
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
    try:
        s3 = get_s3_client()
        bucket, prefix = _get_bucket_and_prefix()
        key = f"{prefix}/{job_id}/input/{filename}" if prefix else f"{job_id}/input/{filename}"
        logger.debug(f"Uploading job input to S3 - Bucket: {bucket}, Key: {key}")
        s3.put_object(Bucket=bucket, Key=key, Body=file_bytes)
        logger.debug(f"Successfully uploaded {key}")
        return key
    except Exception as e:
        logger.error(f"Failed to upload job input to S3: {e}", exc_info=True)
        raise

def download_job_input(key: str) -> bytes:
    try:
        s3 = get_s3_client()
        bucket, _ = _get_bucket_and_prefix()
        logger.debug(f"Downloading job input from S3 - Bucket: {bucket}, Key: {key}")
        response = s3.get_object(Bucket=bucket, Key=key)
        logger.debug(f"Successfully downloaded {key}")
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Failed to download job input from S3: {e}", exc_info=True)
        raise

def upload_job_output(job_id: str, data: dict):
    try:
        s3 = get_s3_client()
        bucket, prefix = _get_bucket_and_prefix()
        key = f"{prefix}/{job_id}/output.json" if prefix else f"{job_id}/output.json"
        logger.debug(f"Uploading job output to S3 - Bucket: {bucket}, Key: {key}")
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(data).encode('utf-8'))
        logger.debug(f"Successfully uploaded {key}")
        return key
    except Exception as e:
        logger.error(f"Failed to upload job output to S3: {e}", exc_info=True)
        raise

def upload_job_prompt(job_id: str, prompt: str):
    try:
        s3 = get_s3_client()
        bucket, prefix = _get_bucket_and_prefix()
        key = f"{prefix}/{job_id}/input/prompt.txt" if prefix else f"{job_id}/input/prompt.txt"
        logger.debug(f"Uploading job prompt to S3 - Bucket: {bucket}, Key: {key}")
        s3.put_object(Bucket=bucket, Key=key, Body=prompt.encode('utf-8'))
        logger.debug(f"Successfully uploaded {key}")
        return key
    except Exception as e:
        logger.error(f"Failed to upload job prompt to S3: {e}", exc_info=True)
        raise

def get_job_data(job_id: str) -> dict:
    s3 = get_s3_client()
    bucket, prefix = _get_bucket_and_prefix()
    
    prompt_key = f"{prefix}/{job_id}/input/prompt.txt" if prefix else f"{job_id}/input/prompt.txt"
    output_key = f"{prefix}/{job_id}/output.json" if prefix else f"{job_id}/output.json"
    
    result = {"prompt": None, "output": None}
    
    try:
        logger.debug(f"Fetching prompt from S3 - Bucket: {bucket}, Key: {prompt_key}")
        prompt_resp = s3.get_object(Bucket=bucket, Key=prompt_key)
        result["prompt"] = prompt_resp['Body'].read().decode('utf-8')
        logger.debug(f"Successfully fetched prompt {prompt_key}")
    except Exception as e:
        logger.debug(f"Failed to fetch prompt {prompt_key} from S3: {e}")
        pass
        
    try:
        logger.debug(f"Fetching output from S3 - Bucket: {bucket}, Key: {output_key}")
        output_resp = s3.get_object(Bucket=bucket, Key=output_key)
        result["output"] = json.loads(output_resp['Body'].read().decode('utf-8'))
        logger.debug(f"Successfully fetched output {output_key}")
    except Exception as e:
        logger.debug(f"Failed to fetch output {output_key} from S3: {e}")
        pass
        
    return result

