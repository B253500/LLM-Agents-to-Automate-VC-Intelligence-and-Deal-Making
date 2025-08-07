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
