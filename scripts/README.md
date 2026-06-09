# Automation Scripts

This directory contains utility scripts to automate local development, testing, data acquisition, and cloud deployment operations.

## Local Development & Testing

*   **`build.zsh`**: Installs frontend and backend dependencies locally (for IDE autocomplete support) and builds the local Docker Compose images.
*   **`initialize-python.zsh`**: Sets up a local Python virtual environment (`venv`) and installs the backend dependencies. Run this before running local tests outside of Docker.
*   **`run_tests.zsh`**: Executes the backend test suite using `pytest` and generates an HTML code coverage report.

## Cloud Deployment (AWS CDK)

*   **`deploy.zsh`**: Synthesizes and deploys the AWS CDK stack to the cloud.
*   **`undeploy.zsh`**: Tears down and destroys the deployed AWS CDK stack.
*   **`start.zsh`**: Starts the AWS ECS API and Worker services by scaling their desired task count up to 1. Usage: `./start.zsh <env_name>`
*   **`stop.zsh`**: Stops the AWS ECS API and Worker services by scaling their desired task count down to 0 (useful for saving compute costs without destroying the database or infrastructure). Usage: `./stop.zsh <env_name>`

## Data Utilities

*   **`download-ttbid.zsh`**: Downloads the label image and application data for a single specific TTB ID.
*   **`bulk-download-ttbid.zsh`**: Downloads label images and application data for a batch of TTB IDs.
