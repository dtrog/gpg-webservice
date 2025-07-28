FROM python:3.11-slim

# Install GPG and other necessary packages
RUN apt-get update && apt-get install -y \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for running the app
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables to disable GPG agent completely
ENV GNUPGHOME=/tmp/gnupg
ENV GPG_AGENT_INFO=""
ENV GPG_TTY=""

# Expose the Flask port
EXPOSE 5000

# Default command runs the Flask app, but can be overridden
CMD ["python", "app.py"]
