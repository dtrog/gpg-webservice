# Multi-service Dockerfile for GPG Webservice monorepo
# Build argument determines which service to build
ARG SERVICE=rest

# =============================================================================
# REST API Service
# =============================================================================
FROM python:3.11-slim AS rest

# Install GPG and other necessary packages
RUN apt-get update && apt-get install -y \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better layer caching
COPY gpg-webservice-rest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gpg-webservice-rest/ .

# Create a non-root user for running the app
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV GNUPGHOME=/tmp/gnupg
ENV GPG_AGENT_INFO=""
ENV GPG_TTY=""
ENV PORT=5555
ENV HOST=0.0.0.0

EXPOSE ${PORT}

CMD ["python", "app.py"]

# =============================================================================
# MCP Server Service
# =============================================================================
FROM node:18-alpine AS mcp

WORKDIR /app

# Copy package files
COPY gpg-webservice-mcp/package*.json ./
COPY gpg-webservice-mcp/tsconfig.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY gpg-webservice-mcp/src ./src

# Build TypeScript
RUN npm run build

# Remove devDependencies after build
RUN npm prune --production

# Set default environment variables
ENV MCP_PORT=3000
ENV MCP_HOST=0.0.0.0
ENV GPG_API_BASE=http://localhost:5555

EXPOSE 3000

CMD ["node", "dist/http-server.js"]

# =============================================================================
# Dashboard Service
# =============================================================================
FROM nginx:alpine AS dashboard

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx configuration template
COPY gpg-webservice-dashboard/nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy config template
COPY gpg-webservice-dashboard/config.template.js /etc/config.template.js

# Copy static files
COPY gpg-webservice-dashboard/index.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/register.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/login.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/profile.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/debug.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/admin.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/admin-login.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/disclaimer.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/css/ /usr/share/nginx/html/css/
COPY gpg-webservice-dashboard/js/ /usr/share/nginx/html/js/

EXPOSE 80

CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && envsubst '${API_URL}' < /etc/config.template.js > /usr/share/nginx/html/js/config.js && nginx -g 'daemon off;'"]

# =============================================================================
# Final stage - select service based on build arg
# =============================================================================
FROM ${SERVICE} AS final
