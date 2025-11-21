# Quick Start Guide

## Docker Compose (Easiest)

```bash
# Start both services
docker-compose up -d

# Access services
open http://localhost:5555          # Landing page
open http://localhost:5555/swagger-ui  # API docs
curl http://localhost:3000/health   # MCP health

# View logs
docker-compose logs -f

# Stop
docker-compose down
```
FFE
## Custom Ports

``                                                               v53E`bash
# Create .env file
cat > .env <<EOF
FLASK_PORT=8000
MCP_PORT=4000
EOF

# Start with custom ports
docker-compose up -d

# Access
open http://localhost:8000
curl http://localhost:4000/health
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Landing Page** | http://localhost:5555 | Main website |
| **Swagger UI** | http://localhost:5555/swagger-ui | API documentation |
| **OpenAI Functions** | http://localhost:5555/openai.json | AI function specs |
| **MCP Health** | http://localhost:3000/health | MCP status check |
| **MCP Endpoint** | http://localhost:3000/mcp | For AI agents |

## Testing

```bash
# Test Flask
curl http://localhost:5555/openai/function_definitions

# Test MCP
curl http://localhost:3000/health

# Test MCP tools list
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | jq

# Run tests
docker-compose --profile test up test-runner
```

## OpenAI Agent SDK Integration

```python
# Install
pip install openai-agents-sdk

# Use
from openai_agents_sdk import Agent
from openai_agents_sdk.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="GPG",
    params={"url": "http://localhost:3000/mcp", "timeout": 30}
) as server:
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        mcp_servers=[server]
    )
    result = await agent.run("Register user alice...")
```

## Environment Variables

```env
# Flask
PORT=5555                 # Flask port
HOST=0.0.0.0             # Flask host
FLASK_ENV=development    # Environment

# MCP
MCP_PORT=3000            # MCP port
MCP_HOST=0.0.0.0        # MCP host
GPG_API_BASE=http://localhost:5555  # Flask URL

# Docker Compose
FLASK_PORT=5555          # Port mapping
MCP_PORT=3000           # Port mapping
```

## Troubleshooting

**Port conflict?**
```bash
# Change ports in .env
FLASK_PORT=8000
MCP_PORT=4000
docker-compose up -d
```

**MCP can't reach Flask?**
```bash
# Check Flask is healthy
docker-compose ps
curl http://localhost:5555/openai/function_definitions

# Check MCP logs
docker-compose logs gpg-mcp-server
```

**Need to rebuild?**
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Docker-Specific Issues

#### Issue: "SERVICE_KEY_PASSPHRASE environment variable is required"

**Root Cause**: Docker container not receiving environment variables from .env file

**Solution Steps**:

1. **Verify .env file exists**:
   ```bash
   ls -la .env
   ```

2. **Generate secrets if missing**:
   ```bash
   ./scripts/generate-secrets.sh
   ```

3. **Verify variable is set** in .env:
   ```bash
   grep SERVICE_KEY_PASSPHRASE .env
   # Should show: SERVICE_KEY_PASSPHRASE=<long-random-string>
   ```

4. **Check docker-compose.yml** has `env_file`:
   ```yaml
   services:
     gpg-webservice:
       env_file:
         - .env     # ← This line should exist
   ```

5. **Restart with explicit environment loading**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

6. **Verify container received the variable**:
   ```bash
   docker exec gpg-webservice-rest-gpg-webservice-1 env | grep SERVICE_KEY_PASSPHRASE
   ```

#### Container Builds But Exits Immediately

**Check logs**:
```bash
docker logs gpg-webservice-rest-gpg-webservice-1
```

**Common causes and fixes**:

| Error in Logs | Cause | Fix |
|---------------|-------|-----|
| "SERVICE_KEY_PASSPHRASE... required" | Missing env var | Run `./scripts/generate-secrets.sh` |
| "No such file or directory: '.env'" | Missing .env file | `cp .env.example .env` |
| "Permission denied" | Volume mount permissions | `chmod 755 gpg_users.db` or delete and recreate |
| "Port already in use" | Port conflict | Change FLASK_PORT in .env |
| "ModuleNotFoundError" | Incomplete build | `docker-compose build --no-cache` |

#### Best Practice: Use Root-Level docker-compose.yml

For the complete system with all 3 services (REST API, MCP Server, Dashboard), use the root-level orchestration:

```bash
# ❌ Don't do this (from gpg-webservice-rest/):
cd gpg-webservice-rest
docker-compose up -d

# ✅ Do this (from root):
cd ..  # Go to /gpg-webservice root
docker-compose up -d
```

The root-level `docker-compose.yml` handles:
- Proper environment variable inheritance
- All 3 services with correct dependencies
- Shared networking
- Service health checks

**Docker Environment Variable Priority**:

Docker Compose loads environment variables in this order (highest priority first):

1. **Environment section** in docker-compose.yml
2. **env_file** directive
3. **.env file** in same directory as docker-compose.yml
4. **Shell environment** variables

Example from root `docker-compose.yml`:
```yaml
services:
  gpg-webservice:
    env_file:
      - .env                         # Root .env
      - ./gpg-webservice-rest/.env   # Service-specific .env
    environment:
      - SERVICE_KEY_PASSPHRASE=${SERVICE_KEY_PASSPHRASE}  # Explicit pass-through
```

## Next Steps

- 📖 [Full Deployment Guide](./DEPLOYMENT.md)
- 🤖 [OpenAI Agent SDK Integration](./gpg-webservice-mcp/OPENAI_AGENT_SDK.md)
- 💻 [Python Examples](./gpg-webservice-mcp/examples/)
- 📋 [Recent Changes](./CHANGES.md)
