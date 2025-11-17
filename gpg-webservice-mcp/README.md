# GPG Webservice MCP Adapter

A Model Context Protocol (MCP) server that adapts the Flask GPG webservice for use with ChatGPT and other MCP-aware clients. This adapter dynamically loads function definitions from the GPG webservice and exposes them as MCP tools.

## Features

- **Dynamic Function Loading**: Automatically fetches and registers all GPG operations from the Flask webservice
- **Seamless Integration**: Works with ChatGPT, Claude Desktop, and other MCP clients
- **Complete GPG Operations**: Supports signing, verification, encryption, decryption, and key management
- **Flexible Authentication**: Supports API keys via environment variables or per-request
- **Zero Code Changes**: Works with existing Flask GPG webservice without modifications

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
   GPG_API_BASE=http://localhost:5000
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
| `GPG_API_BASE` | Yes | `http://localhost:5000` | Base URL of the Flask GPG webservice |
| `GPG_API_KEY` | No | - | Default API key for authenticated operations |

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

### Development Mode

```bash
npm run dev
```

### Production Mode

```bash
npm run build
npm start
```

### Using with Watch Mode (for development)

```bash
npm run watch
```

In another terminal:
```bash
npm start
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
      - GPG_API_BASE=http://gpg-webservice:5000
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

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "gpg-webservice": {
      "command": "node",
      "args": ["/absolute/path/to/gpg-webservice-mcp/dist/index.js"],
      "env": {
        "GPG_API_BASE": "http://localhost:5000",
        "GPG_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Restart Claude Desktop, and the GPG tools will be available.

### ChatGPT Desktop (when MCP support is available)

Configuration will be similar - check ChatGPT's MCP documentation when available.

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

```
┌─────────────────┐
│  MCP Client     │
│ (ChatGPT/Claude)│
└────────┬────────┘
         │ MCP Protocol (stdio)
         ↓
┌─────────────────┐
│  MCP Adapter    │
│  (This Server)  │
└────────┬────────┘
         │ HTTP/JSON
         ↓
┌─────────────────┐
│ Flask GPG       │
│ Webservice      │
└─────────────────┘
```

### Transport Layer: stdio vs HTTP

**Current Implementation**: This MCP server uses **stdio transport** (standard input/output), which is the recommended approach for MCP servers. The server communicates with MCP clients through stdin/stdout, while making HTTP requests to the Flask backend.

**Why stdio?**
- Standard MCP pattern - clients like Claude Desktop expect stdio
- Secure - no network exposure of the MCP server itself
- Simple - no need for port management or HTTPS certificates
- Efficient - direct process communication

**HTTP Transport (Alternative)**:
If you need the MCP server to be network-accessible (e.g., for web-based ChatGPT connections), you would need to:
1. Use `SSEServerTransport` or a custom HTTP transport
2. Add authentication/authorization middleware
3. Handle CORS and security considerations
4. Deploy behind a reverse proxy with HTTPS

The current stdio implementation is suitable for:
- Claude Desktop integration
- Local AI assistants
- Command-line MCP clients
- Any client that can spawn child processes

For network-based ChatGPT connectors, you may need to wrap this server with an HTTP bridge or use a different transport mechanism.

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
│   ├── index.ts        # Main MCP server implementation
│   └── types.ts        # TypeScript type definitions
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript configuration
├── .env.example        # Environment variable template
└── README.md          # This file
```

### Adding Features

The adapter is designed to be maintenance-free. New Flask endpoints are automatically:
- Discovered from `/openai/function_definitions`
- Registered as MCP tools
- Available to clients

No code changes needed in the adapter when the Flask service is updated.

### Testing

Test the server manually:

1. Start the Flask GPG webservice
2. Start the MCP server with `npm run dev`
3. Use an MCP client to call tools

Example with `@modelcontextprotocol/inspector`:

```bash
npm install -g @modelcontextprotocol/inspector
mcp-inspector node dist/index.js
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
