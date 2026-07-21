# TTB Label Compliance Prototype

**Live Deployment: OFFLINE**

Welcome to the TTB Label Compliance prototype. This system automates the verification of alcohol label applications using AI.

For an overview of the system architecture, product discovery, and project assumptions, please see the **[Documentation Overview](docs/Overview.md)**.


## Local Development Environment

The local environment uses Docker Compose to orchestrate the frontend (Vite), backend (FastAPI), database (PostgreSQL), message broker (Redis), and background worker (Celery).

> [!NOTE]
> **Fully Offline Local Development:** Currently, local development relies on an external AWS S3 bucket for object storage and OpenAI for LLM inference. To make local development 100% offline, MinIO support can be added to the Docker Compose stack (as an S3-compatible drop-in replacement) in conjunction with a locally hosted LLM (e.g., Llama 3 via Ollama) using the generic LLM interface.

### Prerequisites

1. **Docker & Docker Compose**: Ensure Docker is installed and running.
2. **Environment Variables**: Create a `.env` file in the root directory containing the required API keys and configuration:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   S3_BUCKET_PATH=your_s3_bucket_name/jobs/
   ```

### Bootstrapping the Environment

1. **Build the Containers & Dependencies**
   Run the build script to install local IDE dependencies and build the Docker images:
   ```bash
   ./scripts/build.zsh
   ```

2. **Start the Services**
   Bring up the entire local stack using Docker Compose:
   ```bash
   docker-compose up
   ```

3. **Access the Application**
   - **Frontend UI:** http://localhost:5173
   - **Backend API:** http://localhost:8080

### Testing
To run the automated test suite locally without Docker, use the initialization and test scripts:
```bash
./scripts/initialize-python.zsh
./scripts/run_tests.zsh
```

For detailed information on deployment and utilities, see the **[Scripts Documentation](scripts/README.md)**.
