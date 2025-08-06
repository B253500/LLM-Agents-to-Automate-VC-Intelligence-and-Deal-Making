# Step 1: Start from a standard, official Python image (which is based on Debian)
FROM python:3.11-slim-bookworm

# Set environment variables
# Prevents npm from creating a log file in the project directory
ENV NPM_CONFIG_LOGLEVEL=warn
# Set the n8n version to install
ENV N8N_VERSION=1.46.0

# Switch to the root user to install system packages
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
COPY minimal_requirements.txt ./

# Step 4: Install your project's Python dependencies
RUN pip install --no-cache-dir -r minimal_requirements.txt

# Step 5: Install Playwright's browser dependencies
RUN playwright install --with-deps

# Copy the rest of your project code into the container
COPY . .

# Create the n8n data directory and set permissions
RUN useradd --create-home --shell /bin/bash node
RUN mkdir /home/node/.n8n && chown -R node:node /home/node/.n8n

# Switch to the non-root 'node' user for security
USER node

# Expose the n8n port
EXPOSE 5678

# Set the default command to start n8n when the container runs
CMD [ "n8n" ]
