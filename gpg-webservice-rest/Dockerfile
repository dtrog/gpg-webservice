FROM python:3.11-slim

# Install GPG and other necessary packages
RUN apt-get update && apt-get install -y \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY gpg-webservice-rest/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gpg-webservice-rest/ .

# Create a non-root user for running the app
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables to disable GPG agent completely
ENV GNUPGHOME=/tmp/gnupg
ENV GPG_AGENT_INFO=""
ENV GPG_TTY=""

# Configure Flask port via environment variable (default 5555)
ENV PORT=5555
ENV HOST=0.0.0.0

# Expose the Flask port (can be overridden)
EXPOSE ${PORT}

# Default command runs the Flask app, but can be overridden
CMD ["python", "app.py"]
