[← Back to Overview](Overview.md)

# General Architecture

The TTB Label Compliance system is built using a modern, decoupled architecture designed to support asynchronous processing for heavy tasks such as OCR and LLM inference.

While the core infrastructure can be spun up locally for development using Docker Compose, it relies on external cloud APIs (such as OpenAI) for LLM capabilities. The system features a generic LLM interface to enable plugging in other LLMs. For production, the system can be deployed to the cloud using AWS CDK. Below is a breakdown of the services, their purposes, and how they map to each environment.

## 1. Frontend
The user interface is a Single Page Application (SPA) built with React and Vite. It allows users to upload label images, provide instructions, and view asynchronous job statuses and details.

- **Local (Docker Compose):** Runs in a dedicated container serving the application on port `5173` via `npm run dev`.
- **AWS CDK:** The production build is hosted as a static website in an **Amazon S3 Bucket** (`FrontendBucket`), which provides low-cost and highly available web hosting.

## 2. Backend API
The core API is built using FastAPI (Python) and Uvicorn. It exposes HTTP endpoints for the frontend to submit jobs, check job status, and retrieve processing results. It is designed to be stateless and fast, delegating long-running tasks to the worker service.

- **Local (Docker Compose):** Runs in a container mapped to port `8080`.
- **AWS CDK:** Runs as an **AWS ECS Fargate Service** behind an **Application Load Balancer (ALB)**. An **API Gateway (HTTP API)** acts as the front door, proxying traffic to the ALB.

## 3. Background Worker
Long-running or computationally heavy processes (like Tesseract OCR, LLM API calls, and evaluation rules) are handled asynchronously by a Celery worker.

- **Local (Docker Compose):** Runs as a standalone container executing the Celery worker process from the shared backend image.
- **AWS CDK:** Runs as an independent **AWS ECS Fargate Service**. It operates without a load balancer since it pulls tasks directly from the message broker. Auto-scaling rules are configured to increase task count based on CPU utilization.

## 4. Relational Database
PostgreSQL is used as the primary relational database to track job states, timestamps, extracted metadata, and rule evaluation results.

- **Local (Docker Compose):** A local `postgres:15` container mapped to port `5432` with a persistent volume (`postgres_data`).
- **AWS CDK:** Managed by **Amazon RDS for PostgreSQL**. Deployed securely within private subnets.

## 5. Message Broker / Cache
Redis is utilized as the message broker for Celery to queue asynchronous tasks, and as a backend to store task states.

- **Local (Docker Compose):** A local `redis:7` container mapped to port `6379`.
- **AWS CDK:** Hosted via **Amazon ElastiCache for Redis**, deployed in a private subnet group.

## 6. Object Storage
Object storage is required to hold the uploaded label images, text, and final extracted JSON data.

- **Local (Docker Compose):** Uses a remote AWS S3 Bucket. The local environment relies on environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_PATH`) to interact with cloud storage directly.
- **AWS CDK:** Provisions a dedicated **Amazon S3 Bucket** (`JobsBucket`) for storage. The ECS tasks are automatically granted IAM permissions to read and write to this bucket securely.

---

## Summary Diagram

| Service Role         | Tech Stack       | Local (Docker Compose) | AWS Deployment (CDK)          |
|----------------------|------------------|------------------------|-------------------------------|
| **Frontend**         | React + Vite     | Node Container         | S3 Static Website Hosting     |
| **Backend API**      | FastAPI (Python) | Python Container       | ECS Fargate + ALB + API GW    |
| **Worker**           | Celery (Python)  | Python Container       | ECS Fargate                   |
| **Database**         | PostgreSQL 15    | Postgres Container     | Amazon RDS (PostgreSQL)       |
| **Message Queue**    | Redis 7          | Redis Container        | Amazon ElastiCache (Redis)    |
| **Object Storage**   | Amazon S3        | Remote S3 Bucket       | Amazon S3                     |
