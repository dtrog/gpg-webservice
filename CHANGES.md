# Recent Changes and Improvements

## Summary

This document summarizes the recent updates to the GPG Webservice project, including MCP HTTP transport support, configurable ports, improved web interface, and enhanced deployment options.

## Major Changes

### 1. Configurable Port Support ✅

**Files Changed:**
- `config.py` - Added `PORT` and `HOST` configuration
- `app.py` - Updated to use configured port/host
- `.env.example` - Added PORT and HOST variables
- `Dockerfile` - Added PORT environment variable support

**Usage:**
```env
PORT=5555  # Flask server port (default: 5000)
HOST=0.0.0.0  # Host address
```

```bash
# Set port via environment
export PORT=5555
python app.py

# Or in Docker
docker run -e PORT=5555 -p 5555:5555 gpg-webservice
```

### 2. MCP HTTP Transport for OpenAI Agent SDK ✅

**New Files:**
- `gpg-webservice-mcp/src/http-server.ts` - HTTP MCP server
- `gpg-webservice-mcp/Dockerfile` - MCP container image
- `gpg-webservice-mcp/OPENAI_AGENT_SDK.md` - Integration guide
- `gpg-webservice-mcp/examples/` - Python examples

**Features:**
- StreamableHTTPServerTransport for network clients
- Compatible with OpenAI Agent SDK's `MCPServerStreamableHttp`
- Health check endpoint at `/health`
- Configurable via `MCP_PORT` and `MCP_HOST`

**Usage:**
```bash
# Start HTTP MCP server
cd gpg-webservice-mcp
npm run start:http

# Connect from Python/OpenAI Agent SDK
from openai_agents_sdk.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="GPG",
    params={"url": "http://localhost:3000/mcp"}
) as server:
    agent = Agent(mcp_servers=[server])
```

### 3. Professional Landing Page ✅

**New Files:**
- `static/index.html` - Complete landing page

**Features:**
- Modern, responsive design
- Feature showcase grid
- API endpoint quick reference
- Technology stack display
- Links to documentation (Swagger UI, GitHub)
- Security notices
- Mobile-friendly

**Access:**
- Local: `http://localhost:5555/`
- Production: `https://your-service.onrender.com/`

### 4. Fixed Swagger UI ✅

**Files Changed:**
- `static/swagger_ui.html` - Updated CDN links and configuration

**Improvements:**
- Fixed broken CDN integrity hashes
- Updated to Swagger UI 5.11.0 from unpkg.com
- Added StandaloneLayout for better UX
- Deep linking support
- Download URL plugin

**Access:**
- `http://localhost:5555/swagger-ui`

### 5. Docker Compose Enhancements ✅

**Files Changed:**
- `docker-compose.yml` - Multi-service setup with health checks

**New Features:**
- Both Flask and MCP services in one compose file
- Configurable ports via environment variables:
  - `FLASK_PORT` (default: 5555)
  - `MCP_PORT` (default: 3000)
- Health checks for both services
- Service dependencies (MCP waits for Flask)
- Shared network for inter-service communication

**Usage:**
```bash
# Default ports (5555 for Flask, 3000 for MCP)
docker-compose up -d

# Custom ports
FLASK_PORT=8000 MCP_PORT=4000 docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### 6. Render.com Deployment Configuration ✅

**Files Changed:**
- `.render.yaml` - Multi-service deployment

**Features:**
- Automatic deployment of both Flask and MCP services
- Persistent disk for database
- Auto-generated secrets
- Health check configuration
- Environment variable management

**Deployment:**
```bash
# Push to GitHub
git push

# Render automatically deploys via Blueprint
# Both services will be available at:
# - https://gpg-webservice.onrender.com
# - https://gpg-mcp-server.onrender.com
```

### 7. Comprehensive Documentation ✅

**New Files:**
- `DEPLOYMENT.md` - Complete deployment guide
- `gpg-webservice-mcp/OPENAI_AGENT_SDK.md` - OpenAI integration
- `gpg-webservice-mcp/examples/README.md` - Example usage

**Updates:**
- `README.md` - Updated with new features
- `gpg-webservice-mcp/README.md` - Added HTTP transport docs

## Breaking Changes

### Port Changes

**Before:**
- Hardcoded port 5555 in `app.py`

**After:**
- Configurable via `PORT` environment variable
- Default: 5000 (production), 5555 (development)

**Migration:**
```bash
# Set environment variable to maintain old behavior
export PORT=5555

# Or update your .env file
echo "PORT=5555" >> .env
```

## New Environment Variables

| Variable | Service | Default | Description |
|----------|---------|---------|-------------|
| `PORT` | Flask | 5000 | Flask server port |
| `HOST` | Flask | 0.0.0.0 | Flask host address |
| `MCP_PORT` | MCP | 3000 | MCP HTTP server port |
| `MCP_HOST` | MCP | 0.0.0.0 | MCP host address |
| `GPG_API_BASE` | MCP | http://localhost:5000 | Flask service URL |

## File Structure Changes

```
gpg-webservice/
├── static/
│   ├── index.html          # NEW: Landing page
│   ├── swagger_ui.html     # UPDATED: Fixed CDN links
│   ├── swagger.json
│   ├── openai.json
│   └── disclaimer.html
├── gpg-webservice-mcp/
│   ├── src/
│   │   ├── index.ts        # EXISTING: stdio transport
│   │   ├── http-server.ts  # NEW: HTTP transport
│   │   └── types.ts
│   ├── examples/           # NEW: Python examples
│   │   ├── openai_agent_example.py
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── Dockerfile          # NEW: MCP container
│   ├── OPENAI_AGENT_SDK.md # NEW: Integration guide
│   └── README.md           # UPDATED: HTTP transport docs
├── config.py               # UPDATED: PORT and HOST config
├── app.py                  # UPDATED: Use configured port
├── Dockerfile              # UPDATED: PORT environment variable
├── docker-compose.yml      # UPDATED: Multi-service + ports
├── .env.example            # UPDATED: New port variables
├── .render.yaml            # UPDATED: Multi-service deployment
├── DEPLOYMENT.md           # NEW: Deployment guide
└── CHANGES.md              # NEW: This file
```

## Testing

All changes have been tested:

✅ Flask server starts on custom port
✅ MCP HTTP server starts and serves tools
✅ Docker Compose builds and runs both services
✅ Health checks work for both services
✅ Landing page displays correctly
✅ Swagger UI loads properly
✅ OpenAI Agent SDK can connect to MCP server
✅ Example scripts run successfully

## Upgrade Guide

### From Previous Version

1. **Update environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env to set PORT and other variables
   ```

2. **Rebuild Docker images:**
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

3. **Update any hardcoded port references:**
   - Change port 5555 references to use environment variable
   - Update client code to use new default port (5000) or configure PORT

4. **For Render deployment:**
   - Push updated `.render.yaml` to GitHub
   - Render will automatically detect and deploy both services

## Future Enhancements

Potential improvements for future versions:

- [ ] PostgreSQL support for production
- [ ] Redis caching for function definitions
- [ ] WebSocket support for real-time operations
- [ ] Prometheus metrics endpoint
- [ ] Admin dashboard UI
- [ ] Bulk operations API
- [ ] Key rotation/expiry management
- [ ] Multi-tenant support

## Support

For issues or questions:
- GitHub Issues: [dtrog/gpg-webservice](https://github.com/dtrog/gpg-webservice)
- Documentation: See README.md and DEPLOYMENT.md
- Examples: See `gpg-webservice-mcp/examples/`

## Version

**Current Version:** 1.1.0 (with MCP HTTP transport and configurable ports)

**Previous Version:** 1.0.0 (stdio transport only, hardcoded ports)

**Release Date:** November 2025
