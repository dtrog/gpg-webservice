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

## Custom Ports

```bash
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

## Next Steps

- 📖 [Full Deployment Guide](./DEPLOYMENT.md)
- 🤖 [OpenAI Agent SDK Integration](./gpg-webservice-mcp/OPENAI_AGENT_SDK.md)
- 💻 [Python Examples](./gpg-webservice-mcp/examples/)
- 📋 [Recent Changes](./CHANGES.md)
