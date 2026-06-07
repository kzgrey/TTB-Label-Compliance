from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/jobsdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    S3_BUCKET_PATH: str = "my-jobs-bucket/"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: str | None = None  # Used for local MinIO
    OPENAI_API_KEY: str = ""
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
