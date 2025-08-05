FROM n8nio/n8n:latest

# Switch to root to install system packages
USER root

# Install Python3, pip and Playwright dependencies (Alpine commands)
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages playwright && \
    npx playwright install --with-deps

# Back to the n8n user
USER node
