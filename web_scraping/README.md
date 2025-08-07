# Web Scraping Workflow

This directory contains the automated web scraping and data collection workflow for VC reports and market data.

**Note:** This workflow is designed to be run via n8n inside a Docker container. 

## How It Works

The scraping process is designed to be incremental and avoid re-downloading existing content. Here is a step-by-step breakdown of the logic:

1.  **Orchestration**: The `download_reports.py` script acts as the main orchestrator. When executed by the n8n workflow, it systematically calls the individual scraper modules located in the `scripts/` directory (e.g., `download_techcrunch.py`).

2.  **Caching and Duplicate Check**: Before scraping a source, each script first reads a corresponding JSON tracking file (e.g., `data/techcrunch_downloaded.json`). This file contains a list of all the article URLs that have been successfully downloaded in the past. The script loads these URLs into memory to form a "seen" list.

3.  **Scraping New Content**: The script then begins to scrape the target website. For each article or report it finds, it checks if the URL is already in the "seen" list.
    *   If the URL is **already in the list**, the scraper skips it and moves to the next one.
    *   If the URL is **new**, the scraper proceeds to download the content.

4.  **Data Storage**:
    *   **PDF Reports**: The content of the new article is saved as a PDF file inside the `web_scraping/data/vc_reports/` directory. This directory is mapped as a persistent Docker volume, so the files are saved directly to your local machine and are not lost when the container stops.
    *   **Updating the Cache**: Immediately after a successful download, the script updates the JSON tracking file, adding the URL of the newly downloaded report. This ensures that the same report will be skipped in all future runs.

This caching mechanism ensures that the workflow is efficient, only ever processing new reports.

## Web Scraping & n8n Docker Setup

This setup is for running the automated web scraping workflows using Docker and n8n. It is isolated from your local Python environment.

#### 1. Docker and Docker Compose
Ensure you have Docker and Docker Compose installed on your system.
- [Install Docker](https://docs.docker.com/get-docker/)
- [Install Docker Compose](https://docs.docker.com/compose/install/)

#### 2. Build and Run the Docker Container
The n8n services are defined in the `docker-compose.n8n.yml` file. The Dockerfile for n8n (`n8n/Dockerfile`) is configured to use a minimal set of dependencies.

```bash
# Build and run the n8n container in detached mode
docker-compose -f docker-compose.n8n.yml up --build -d
```

### Dependency Management for Docker

The automated web scraping workflow runs inside a custom Docker container orchestrated by `docker-compose`. The dependencies for this isolated environment are managed as follows:

1.  **`web_scraping/minimal_requirements.txt`**: This file is crucial. It contains the lean, specific set of Python packages required for the web scraper to function (e.g., `playwright`, `playwright-stealth`). This ensures the Docker image is as small and efficient as possible. You do not need to install these packages locally if you are only using the Dockerized workflow.

2.  **`n8n/Dockerfile`**: This is the blueprint for building the n8n service container. It contains the instructions that set up the environment. The key steps related to dependencies are:
    ```dockerfile
    # 1. Copy the minimal requirements file into the container's temporary directory
    COPY web_scraping/minimal_requirements.txt /tmp/minimal_requirements.txt

    # 2. Install only those packages using pip
    RUN pip install --no-cache-dir -r /tmp/minimal_requirements.txt
    ```

3.  **`docker-compose.n8n.yml`**: This file starts the build process. When you run `docker-compose ... up --build`, it tells Docker to read the `n8n/Dockerfile` and execute the steps above, creating the final, runnable n8n service with all the correct Python packages installed.

This setup ensures that the web scraping environment is consistent, reproducible, and isolated from your local machine's configuration.

## Usage

This script is **not intended to be run manually**.

To run the web scraping pipeline, please follow the instructions in the main project `README.md` file located in the root directory.

### For Debugging

If you need to debug this script specifically, you can execute it within the running n8n Docker container:
```bash
# First, find the name of your n8n container
docker-compose -f ../docker-compose.n8n.yml ps

# Then, execute the script inside the container
docker exec -it <your_n8n_container_name> python3 web_scraping/download_reports.py
```
