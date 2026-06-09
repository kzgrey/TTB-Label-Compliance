# Overview

Welcome to the TTB Label Compliance system documentation.

This project uses a modern, decoupled architecture designed to process label images asynchronously and apply compliance rules.

## Documentation Index

- [Architecture Document](Architecture.md): Detailed explanation of the system's architecture, including which services are running (Frontend, Backend, Worker, Database, Redis, Object Storage) and how they map to both local (Docker Compose) and cloud (AWS CDK) environments.
- [Discovery & Pre-Implementation Clarifications](DiscoveryClarifications.md): A record of the product discovery phase conducted before coding began. It provides evidence of engineering leadership considerations, such as evaluating whether to salvage the failed vendor pilot and proposing automated asynchronous COLA ingestion instead of a manual synchronous workflow.
- [Critical Analysis](CriticalAnalysis.md): Evaluates the prototype against business requirements. Highlights how the 5-second latency rule drove the architecture, explains the cost-efficiency of using OpenAI (due to the system being idle 95% of the time), discusses handling nuanced data matching, and identifies risks like visual formatting validation.
- [Assumptions and Constraints](AssumptionsAndConstraints.md): Concisely lists the project boundaries, including input formats, network/security limitations, LLM equivalence rules, and low-confidence fail-safes.
- [Extensibility Guide](ExtensibilityGuide.md): Explains how to add compliance rules and validation logic for new beverage classes (e.g., Wine, Beer).
- [Engineering Trade-offs](EngineeringTradeoffs.md): Details the lower-level tech stack rationale, defending choices like FastAPI vs. Django, Celery vs. SQS, and Tesseract vs. Cloud Vision APIs.
- [Reviewer's Guide & Test Cases](ReviewersGuide.md): A guide for evaluating the prototype, outlining expected system behaviors across clean passes, semantic equivalences, hard failures, and distorted images.
- [Enterprise Deployment & Security](EnterpriseDeploymentAndSecurity.md): Outlines the operational roadmap for moving to production, covering FedRAMP security requirements (encryption, secrets management), CI/CD operations, and COLA API integration strategies.
