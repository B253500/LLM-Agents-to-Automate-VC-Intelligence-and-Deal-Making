# Step 1: Start from a standard, official Python image (which is based on Debian)
FROM python:3.11-slim-bookworm

# Set environment variables
ENV NPM_CONFIG_LOGLEVEL=warn
ENV N8N_VERSION=1.46.0

# Switch to the root user for all system-level installations
USER root

# Step 2: Install Node.js, npm, and other necessary system tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Step 3: Install n8n using npm
RUN npm install -g n8n@${N8N_VERSION}

# Set the working directory for the rest of the commands
WORKDIR /data

# Copy your project's requirements file
COPY web_scraping/minimal_requirements.txt ./

# Step 4: Install your project's Python dependencies
RUN pip install --no-cache-dir -r minimal_requirements.txt

# Step 5: Install Playwright's SYSTEM dependencies as root
RUN playwright install-deps

# Copy the rest of your project code into the container
COPY . .

# Create the node user that n8n will run as
RUN useradd --create-home --shell /bin/bash node

# Create the n8n data directory and set permissions
RUN mkdir -p /home/node/.n8n && chown -R node:node /home/node/.n8n

# Switch to the new user
USER node

# Step 6: Install the BROWSERS themselves as the node user
RUN playwright install

# Expose the n8n port
EXPOSE 5678

# Set the default command to start n8n when the container runs
CMD [ "n8n" ]
