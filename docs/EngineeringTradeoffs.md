[← Back to Overview](Overview.md)

# Engineering Trade-offs & Tech Stack Rationale

This document outlines the lower-level software engineering decisions made during the development of this prototype, focusing on why specific technologies were chosen over alternatives.

## Backend: FastAPI vs. Django
**Choice:** FastAPI
**Rationale:** The core requirement of this application is serving as an asynchronous ingestion API that orchestrates long-running background tasks. FastAPI's native support for Python `asyncio`, high performance, and automatic OpenAPI (Swagger) documentation generation makes it vastly superior to Django for building decoupled microservices. Django's heavy ORM and synchronous default design would be overkill for a system primarily shuffling JSON and images.

## Background Tasks: Celery + Redis vs. AWS SQS / Native Asyncio
**Choice:** Celery + Redis
**Rationale:** While native `asyncio.create_task` is fast, it lacks persistence; if the container crashes, the OCR job is lost. AWS SQS provides persistence but locks the application into the AWS ecosystem. Celery backed by Redis provides a cloud-agnostic, robust task queue with built-in retries, failure handling, and state tracking (via Celery result backends). This guarantees jobs are never lost, even during high-volume bursts.

## Frontend: React + Vite vs. Server-Side Rendering (Next.js)
**Choice:** React + Vite (Single Page Application)
**Rationale:** The UI is an internal-facing compliance tool. SEO is irrelevant, and the dashboard relies heavily on client-side state (polling for job updates, displaying dynamic validation tables). A Vite-bundled React SPA provides the fastest, most responsive user experience without the overhead of maintaining a Node.js server for Server-Side Rendering (SSR).

## OCR: Tesseract vs. Cloud Vision APIs
**Choice:** Tesseract (Local)
**Rationale:** Used to minimize outbound network calls and eliminate per-page OCR costs. While Cloud Vision APIs are more accurate on distorted images, Tesseract is completely free and executes in <1 second locally, leaving the 5-second SLA window open for the LLM extraction phase.
