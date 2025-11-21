# Deployment Guide

This guide covers deploying the GPG Webservice and optional MCP server to various platforms.

## Table of Contents

- [Docker Compose (Local)](#docker-compose-local)
- [Render.com Deployment](#rendercom-deployment)
- [Environment Variables](#environment-variables)
- [Port Configuration](#port-configuration)

## Docker Compose (Local)

### Quick Start

```bash
# Create .env file with custom ports
cp .env.example .env

# Edit .env to set ports (optional)
# FLASK_PORT=5555
# MCP_PORT=3000

# Start both services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services

The docker-compose setup includes:

1. **gpg-webservice** (Flask API)
   - Default port: 5555 (configurable via `FLASK_PORT`)
   - Health check: `/openai/function_definitions`
   - Web UI: `http://localhost:5555`

2. **gpg-mcp-server** (MCP HTTP Server)
   - Default port: 3000 (configurable via `MCP_PORT`)
   - Health check: `/health`
   - MCP endpoint: `http://localhost:3000/mcp`
   - Depends on Flask service

3. **test-runner** (Tests only)
   - Run with: `docker-compose --profile test up test-runner`

### Configuring Ports

Create or edit `.env` file:

```env
# Flask service port
FLASK_PORT=5555

# MCP service port
MCP_PORT=3000

# Other settings...
FLASK_ENV=development
```

Then start services:

```bash
docker-compose up -d
```

Access services at:
- Flask: http://localhost:5555
- MCP: http://localhost:3000/mcp

### Testing

```bash
# Test Flask service
curl http://localhost:5555/

# Test MCP service
curl http://localhost:3000/health

# Run unit tests
docker-compose --profile test up test-runner
```

## Render.com Deployment

### Prerequisites

1. GitHub repository with this code
2. Render.com account (free tier available)

### Deployment Steps

#### Option 1: Using render.yaml (Recommended)

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Add deployment configuration"
   git push
   ```

2. **Connect to Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `.render.yaml`

3. **Configure Environment Variables**

   In the Render dashboard, update these for `gpg-webservice`:
   - `PORT`: 5000 (Render default)
   - `SECRET_KEY`: (auto-generated)
   - `OPENAI_API_KEY`: Your OpenAI key (if using AI features)

   For `gpg-mcp-server`:
   - `GPG_API_BASE`: `https://your-flask-service.onrender.com`
   - `MCP_PORT`: 3000

4. **Deploy**
   - Click "Apply" to deploy both services
   - Wait for builds to complete (~5-10 minutes)

#### Option 2: Manual Deployment

**Deploy Flask Service:**

1. Dashboard → "New" → "Web Service"
2. Connect repository
3. Configure:
   - Name: `gpg-webservice`
   - Runtime: Docker
   - Dockerfile Path: `./Dockerfile`
   - Port: Use `PORT` from environment
4. Add environment variables (see above)
5. Click "Create Web Service"

**Deploy MCP Server (Optional):**

1. Dashboard → "New" → "Web Service"
2. Connect same repository
3. Configure:
   - Name: `gpg-mcp-server`
   - Runtime: Docker
   - Dockerfile Path: `./gpg-webservice-mcp/Dockerfile`
   - Port: 3000
4. Environment variables:
   - `MCP_PORT=3000`
   - `GPG_API_BASE=https://your-flask-service.onrender.com`
5. Click "Create Web Service"

### Post-Deployment

1. **Get Service URLs**
   - Flask: `https://gpg-webservice.onrender.com`
   - MCP: `https://gpg-mcp-server.onrender.com`

2. **Update MCP Configuration**
   - In Render dashboard, update `gpg-mcp-server` environment variable:
   - `GPG_API_BASE=https://your-actual-flask-url.onrender.com`
   - Restart the MCP service

3. **Test Deployment**
   ```bash
   # Test Flask
   curl https://your-service.onrender.com/

   # Test MCP
   curl https://your-mcp-service.onrender.com/health
   ```

## Environment Variables

### Flask Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 5000 | Flask server port |
| `HOST` | No | 0.0.0.0 | Host address to bind |
| `FLASK_ENV` | No | production | Environment (development/production) |
| `SECRET_KEY` | Yes (prod) | Auto-generated | Flask secret key |
| `DATABASE_URL` | No | sqlite:///gpg_users.db | Database connection string |
| `OPENAI_API_KEY` | No | - | OpenAI API key (optional) |

### MCP Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_PORT` | No | 3000 | MCP HTTP server port |
| `MCP_HOST` | No | 0.0.0.0 | Host address to bind |
| `GPG_API_BASE` | Yes | - | Flask service URL |

## Port Configuration

### Development (Docker Compose)

Ports are configurable via environment variables:

```env
# .env file
FLASK_PORT=5555  # Any available port
MCP_PORT=3000    # Any available port
```

Port mapping in docker-compose.yml:
```yaml
ports:
  - "${FLASK_PORT:-5555}:${FLASK_PORT:-5555}"
```

### Production (Render/Cloud)

**Render:**
- Flask: Use `PORT` environment variable (Render sets this automatically)
- MCP: Use `MCP_PORT` (default 3000)

**Other Platforms:**
- Most cloud platforms (Heroku, Railway, etc.) provide a `PORT` environment variable
- The app will automatically use this port

## Health Checks

### Flask Service
```bash
curl http://localhost:5555/openai/function_definitions
```

Should return JSON with function definitions.

### MCP Service
```bash
curl http://localhost:3000/health
```

Should return:
```json
{
  "status": "healthy",
  "service": "gpg-webservice-mcp",
  "version": "1.0.0",
  "transport": "http",
  "tools_loaded": 6
}
```

## Troubleshooting

### Port Already in Use

**Error**: `Address already in use`

**Solution**: Change port in `.env`:
```env
FLASK_PORT=5556  # Use different port
```

### MCP Can't Connect to Flask

**Error**: MCP health check fails

**Solution**: Check `GPG_API_BASE` environment variable:
```bash
# Docker Compose (internal networking)
GPG_API_BASE=http://gpg-webservice:5555

# Production (external URL)
GPG_API_BASE=https://your-flask-service.onrender.com
```

### Database Permission Issues

**Error**: `OperationalError: unable to open database file`

**Solution**: Ensure data directory is writable:
```bash
# Docker Compose
docker-compose down -v  # Remove volumes
docker-compose up -d    # Recreate with correct permissions
```

### Swagger UI Not Loading

**Error**: Swagger UI shows blank page

**Solution**: Check browser console for CDN errors. The fixed swagger_ui.html uses unpkg.com CDN which should work reliably.

## Scaling Considerations

### Free Tier Limitations (Render.com)

- Services sleep after 15 minutes of inactivity
- Cold start time: ~30 seconds
- No persistent disk on free tier (use external database for production)

### Production Recommendations

1. **Use PostgreSQL** instead of SQLite:
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/gpgdb
   ```

2. **Deploy behind CDN/Reverse Proxy** (Cloudflare, nginx)

3. **Enable HTTPS** (handled automatically by Render/most platforms)

4. **Set up monitoring** (Render provides basic metrics)

5. **Use persistent storage** for database (Render disk or external DB)

## Security Checklist

- [ ] `SECRET_KEY` is set to a strong random value
- [ ] `FLASK_ENV=production` in production
- [ ] Database credentials are in environment variables (not code)
- [ ] HTTPS is enabled (automatic on Render)
- [ ] Rate limiting is enabled (default: 30 req/min)
- [ ] API keys are never committed to git
- [ ] Security headers are enabled (default: true)

## Next Steps

- [Using with OpenAI Agent SDK](./gpg-webservice-mcp/OPENAI_AGENT_SDK.md)
- [MCP Integration Guide](./gpg-webservice-mcp/README.md)
- [API Documentation](http://localhost:5555/swagger-ui) (when running)
