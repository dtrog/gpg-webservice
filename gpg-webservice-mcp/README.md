# GPG Webservice MCP Adapter

A Model Context Protocol (MCP) server that adapts the Flask GPG webservice for use with ChatGPT and other MCP-aware clients. This adapter dynamically loads function definitions from the GPG webservice and exposes them as MCP tools.

## Features

- **Dynamic Function Loading**: Automatically fetches and registers all GPG operations from the Flask webservice
- **Seamless Integration**: Works with OpenAI Agent SDK, Claude Desktop, ChatGPT, and other MCP clients
- **Dual Transport Support**: stdio for local clients, HTTP for network/agent integrations
- **Complete GPG Operations**: Supports signing, verification, encryption, decryption, and key management
- **Flexible Authentication**: Supports API keys via environment variables or per-request
- **Zero Code Changes**: Works with existing Flask GPG webservice without modifications
- **Production Ready**: Supports deployment behind HTTPS proxies for secure remote access

## Available Operations

The MCP server dynamically exposes these tools from the Flask webservice:

- `register_user` - Register a new user with automatic GPG key generation
- `sign_text` - Sign text content using user's private GPG key
- `verify_text_signature` - Verify a text signature against a public key
- `encrypt_text` - Encrypt text for a recipient using their public key
- `decrypt_text` - Decrypt text using user's private key
- `get_user_public_key` - Get the authenticated user's public GPG key

## Prerequisites

- Node.js >= 18.0.0
- npm or yarn
- Running Flask GPG webservice instance

## Installation

1. **Clone or navigate to the directory**:
   ```bash
   cd gpg-webservice-mcp
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set:
   ```env
   GPG_API_BASE=http://localhost:5555
   # Optional: Set a default API key
   # GPG_API_KEY=your-api-key-here
   ```

4. **Build the TypeScript code**:
   ```bash
   npm run build
   ```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GPG_API_BASE` | Yes | `http://localhost:5555` | Base URL of the Flask GPG webservice |
| `GPG_API_KEY` | No | - | Default API key for authenticated operations |
| `MCP_PORT` | No (HTTP only) | `3000` | Port for HTTP transport server |
| `MCP_HOST` | No (HTTP only) | `0.0.0.0` | Host address for HTTP transport (use `0.0.0.0` for external access) |

### Getting an API Key

To use authenticated operations (signing, encryption, etc.), you need an API key:

1. Register a user via the Flask webservice:
   ```bash
   curl -X POST http://localhost:5000/openai/register_user \
     -H "Content-Type: application/json" \
     -d '{
       "username": "myuser",
       "password": "MySecurePass123!",
       "email": "user@example.com"
     }'
   ```

2. The response will include an `api_key` - save this securely (it's only shown once)

3. Set it in your `.env` file:
   ```env
   GPG_API_KEY=your-api-key-from-registration
   ```

## Running the Server

The MCP adapter supports two transport modes:

### 1. stdio Transport (Default - for Claude Desktop, etc.)

**Development Mode:**
```bash
npm run dev
```

**Production Mode:**
```bash
npm run build
npm start
```

### 2. HTTP Transport (for ChatGPT, web-based clients)

**Development Mode:**
```bash
npm run dev:http
```

**Production Mode:**
```bash
npm run build
npm run start:http
```

The HTTP server will start on `http://0.0.0.0:3000` by default with these endpoints:
- `/mcp` - Main MCP endpoint for ChatGPT connections
- `/health` - Health check endpoint

### Using with Watch Mode (for development)

```bash
npm run watch
```

In another terminal:
```bash
# For stdio transport
npm start

# For HTTP transport
npm run start:http
```

## Deployment

### Local Deployment

The MCP server uses stdio transport and is designed to be launched by MCP clients (like Claude Desktop or ChatGPT).

### Docker Deployment (alongside Flask service)

You can add the MCP server to your existing Docker Compose setup:

```yaml
# Add to docker-compose.yml
services:
  gpg-webservice:
    # ... existing Flask service config ...

  gpg-mcp-server:
    build:
      context: ./gpg-webservice-mcp
      dockerfile: Dockerfile
    environment:
      - GPG_API_BASE=http://gpg-webservice:5555
      - GPG_API_KEY=${GPG_API_KEY}
    depends_on:
      - gpg-webservice
    stdin_open: true
    tty: true
```

Create `gpg-webservice-mcp/Dockerfile`:
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY tsconfig.json ./
COPY src ./src
RUN npm run build

CMD ["node", "dist/index.js"]
```

### Cloud Deployment

For production deployments, ensure:

1. **Secure API Base URL**: Use HTTPS for the Flask webservice
   ```env
   GPG_API_BASE=https://your-gpg-service.com
   ```

2. **Environment-based Configuration**: Use your platform's secrets management
   - Heroku: `heroku config:set GPG_API_BASE=...`
   - AWS: Use Parameter Store or Secrets Manager
   - Render: Use environment variables in dashboard

3. **Health Checks**: The server logs startup messages to stderr for monitoring

## Using with MCP Clients

### OpenAI Agent SDK

For detailed integration with OpenAI's Agent SDK (Python), see [OPENAI_AGENT_SDK.md](./OPENAI_AGENT_SDK.md).

**Quick Start:**
```bash
# 1. Install Python SDK
pip install openai-agents

# 2. Start MCP HTTP server
npm run start:http

# 3. Run the example
export OPENAI_API_KEY=your-key
python examples/openai_agent_example.py
```

**Quick Example:**
```python
from openai_agents_sdk import Agent
from openai_agents_sdk.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="GPG Webservice",
    params={"url": "http://localhost:3000/mcp", "timeout": 30},
) as mcp_server:
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        instructions="You help users with GPG cryptographic operations.",
        mcp_servers=[mcp_server],
    )
    result = await agent.run("Register user alice with password SecurePass123!")
```

See [examples/](./examples/) directory for complete working examples.

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "gpg-webservice": {
      "command": "node",
      "args": ["/absolute/path/to/gpg-webservice-mcp/dist/index.js"],
      "env": {
        "GPG_API_BASE": "http://localhost:5555",
        "GPG_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Restart Claude Desktop, and the GPG tools will be available.

### ChatGPT and Web-Based Clients

For ChatGPT and other web-based clients, use the HTTP transport:

1. **Start the HTTP server**:
   ```bash
   npm run build
   npm run start:http
   ```

2. **Server will be available at**:
   ```
   http://localhost:3000/mcp
   ```
   
   **Production endpoint**:
   ```
   https://vps-b5527a39.vps.ovh.net/mcp
   ```

3. **For external access** (deploy to a server):
   - Set `MCP_HOST=0.0.0.0` in `.env`
   - Deploy behind HTTPS reverse proxy (nginx, Caddy, etc.)
   - Configure ChatGPT to connect to `https://your-domain.com/mcp`

4. **Health check**:
   ```bash
   curl http://localhost:3000/health
   ```

**Example nginx configuration for HTTPS**:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp {
        proxy_pass http://localhost:3000/mcp;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Custom MCP Client

```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const transport = new StdioClientTransport({
  command: 'node',
  args: ['/path/to/gpg-webservice-mcp/dist/index.js'],
  env: {
    GPG_API_BASE: 'http://localhost:5000',
    GPG_API_KEY: 'your-api-key-here'
  }
});

const client = new Client({
  name: 'my-client',
  version: '1.0.0'
}, {
  capabilities: {}
});

await client.connect(transport);

// List available tools
const tools = await client.listTools();

// Call a tool
const result = await client.callTool({
  name: 'sign_text',
  arguments: {
    text: 'Hello, World!'
  }
});
```

## Architecture

### stdio Transport (Local Clients)
```
┌─────────────────┐
│  MCP Client     │
│ (Claude Desktop)│
└────────┬────────┘
         │ MCP Protocol (stdio)
         ↓
┌─────────────────┐
│  MCP Adapter    │
│  (index.ts)     │
└────────┬────────┘
         │ HTTP/JSON
         ↓
┌─────────────────┐
│ Flask GPG       │
│ Webservice      │
└─────────────────┘
```

### HTTP Transport (Network Clients)
```
┌─────────────────┐
│  OpenAI Agent   │
│  SDK / ChatGPT  │
└────────┬────────┘
         │ MCP Protocol (HTTP/SSE)
         ↓
┌─────────────────┐
│  MCP HTTP       │
│  Server         │
│  (http-server.ts)│
└────────┬────────┘
         │ HTTP/JSON
         ↓
┌─────────────────┐
│ Flask GPG       │
│ Webservice      │
└─────────────────┘
```

### Transport Layer: stdio vs HTTP

This MCP server supports **two transport modes**:

#### 1. stdio Transport (Default)

**Use Case**: Local clients like Claude Desktop, VS Code, Cursor

**How to run**: `npm start` or `npm run dev`

**Advantages**:
- Standard MCP pattern - clients like Claude Desktop expect stdio
- Secure - no network exposure of the MCP server itself
- Simple - no need for port management or HTTPS certificates
- Efficient - direct process communication

**Best for**:
- Claude Desktop integration
- Local AI assistants
- Command-line MCP clients
- Any client that can spawn child processes

#### 2. HTTP Transport (Network-Accessible)

**Use Case**: Network-based clients like ChatGPT, web applications, remote connections

**How to run**: `npm run start:http` or `npm run dev:http`

**Implementation**: Uses StreamableHTTPServerTransport from the MCP SDK

**Endpoints**:
- `POST /mcp` - Main MCP protocol endpoint
- `GET /health` - Health check endpoint

**Configuration**:
```env
MCP_PORT=3000        # Port to listen on
MCP_HOST=0.0.0.0     # Host address (0.0.0.0 for external access)
```

**Best for**:
- ChatGPT integrations
- Web-based MCP clients
- Remote access scenarios
- Microservices architectures

**Security Considerations for HTTP Mode**:
- Deploy behind a reverse proxy with HTTPS in production
- Implement authentication/authorization if needed
- Configure CORS appropriately for your use case
- Use environment-based secrets management
- Consider rate limiting at the proxy level

### How It Works

1. **Startup**: The MCP server fetches function definitions from `/openai/function_definitions` and uses the `base_url` returned by Flask
2. **Tool Registration**: Each function is registered as an MCP tool with its schema
3. **Tool Invocation**: When a tool is called:
   - Parameters are validated against the schema
   - API key is added to the request header (from env or per-request)
   - HTTP POST is made to the Flask endpoint at the dynamically discovered base URL
   - Response is formatted for the MCP client
4. **Response Formatting**: Flask responses are converted to MCP format with both human-readable text and structured JSON data for AI model consumption

## Error Handling

The adapter provides clear error messages for common issues:

- **Network Errors**: When the Flask service is unreachable
- **Authentication Errors**: When API key is missing or invalid
- **Validation Errors**: When parameters don't match the schema
- **GPG Errors**: When cryptographic operations fail

All errors include error codes and human-readable messages.

## Development

### Project Structure

```
gpg-webservice-mcp/
├── src/
│   ├── index.ts        # stdio transport MCP server
│   ├── http-server.ts  # HTTP transport MCP server
│   └── types.ts        # TypeScript type definitions
├── examples/           # Example integrations
│   ├── openai_agent_example.py  # OpenAI Agent SDK example
│   ├── requirements.txt         # Python dependencies
│   └── README.md               # Examples documentation
├── dist/               # Compiled JavaScript output
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript configuration
├── .env.example        # Environment variable template
├── README.md          # This file
└── OPENAI_AGENT_SDK.md # OpenAI Agent SDK integration guide
```

### Adding Features

The adapter is designed to be maintenance-free. New Flask endpoints are automatically:
- Discovered from `/openai/function_definitions`
- Registered as MCP tools
- Available to clients

No code changes needed in the adapter when the Flask service is updated.

### Testing

#### Testing Locally (without Docker)

1. Start the Flask GPG webservice
2. Start the MCP server with `npm run dev`
3. Use an MCP client to call tools

Example with `@modelcontextprotocol/inspector`:

```bash
npm install -g @modelcontextprotocol/inspector
mcp-inspector node dist/index.js
```

#### Testing with Docker

When running services via Docker Compose, you can test the MCP server in several ways:

> **Note:** The Docker container runs the HTTP transport (`http-server.js`) by default, not the stdio transport. The `mcp-inspector` tool requires stdio transport, so it won't work directly with the Dockerized version. Instead, use the methods below to test the HTTP-based deployment.

**Method 1: Test Flask API Endpoints Directly**

The easiest way to test the Docker deployment:

```bash
# Start all services
docker compose up -d

# Check MCP server is running
curl http://localhost:3000/health

# List available function definitions
curl http://localhost:5555/openai/function_definitions | jq

# Register a test user
curl -X POST http://localhost:5555/openai/register_user \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123!"}'

# Login to get an API key
curl -X POST http://localhost:5555/openai/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123!"}'

# Use the API key for signing text
curl -X POST http://localhost:5555/openai/sign_text \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{"text":"Hello, World!"}'
```

**Method 2: Test via HTTP Transport**

If using the HTTP transport (`http-server.ts`), you can test directly:

```bash
# Start services
docker compose up -d

# Test health endpoint
curl http://localhost:3000/health

# Use the MCP endpoint with any HTTP client
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**Method 3: Test from Host Machine**

Connect to the Dockerized services from your host:

```bash
# Install inspector globally on host
npm install -g @modelcontextprotocol/inspector

# Build MCP locally to test against Dockerized REST API
cd gpg-webservice-mcp
npm run build

# Update .env to point to Docker service
# GPG_API_BASE=http://localhost:5555

# Run inspector
mcp-inspector node dist/index.js
```

**Method 4: View MCP Server Logs**

```bash
# View real-time logs
docker logs -f gpg-webservice-mcp

# Check if server started successfully
docker logs gpg-webservice-mcp | grep "MCP Server started"
```

## Troubleshooting

### "Failed to fetch function definitions"

- Ensure Flask GPG webservice is running
- Check `GPG_API_BASE` points to the correct URL
- Verify `/openai/function_definitions` endpoint is accessible

### "API key required" errors

- Set `GPG_API_KEY` in `.env`, or
- Ensure your MCP client passes the API key per-request

### "Unknown tool" errors

- Restart the MCP server to reload function definitions
- Verify the Flask service has the endpoint registered

### TypeScript compilation errors

```bash
npm run clean
npm install
npm run build
```

## Security Considerations

1. **API Keys**: Never commit `.env` files with real API keys
2. **HTTPS**: Use HTTPS for production Flask services
3. **Rate Limiting**: The Flask service implements rate limiting (30 req/min/IP)
4. **Secrets Management**: Use proper secrets management in production
5. **Network Security**: Restrict access to the Flask service in production

## License

MIT

## Contributing

Contributions are welcome! This adapter is designed to work with the Flask GPG webservice at [dtrog/gpg-webservice](https://github.com/dtrog/gpg-webservice).

## Support

For issues with:
- **This MCP adapter**: Open an issue in the gpg-webservice-mcp repository
- **Flask GPG webservice**: Open an issue at dtrog/gpg-webservice
- **MCP protocol**: See [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk)
