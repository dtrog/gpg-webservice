# Using GPG Webservice MCP with OpenAI Agent SDK

This guide shows how to integrate the GPG Webservice MCP server with OpenAI's Agent SDK to give your AI agents GPG cryptographic capabilities.

## Overview

The OpenAI Agent SDK supports MCP (Model Context Protocol) servers through the `MCPServerStreamableHttp` transport, which works perfectly with our HTTP-based MCP server.

## Prerequisites

1. **Python 3.10+** with OpenAI Agent SDK installed:
   ```bash
   pip install openai-agents
   ```

2. **Running MCP HTTP Server**:
   ```bash
   cd gpg-webservice-mcp
   npm run build
   npm run start:http
   ```
   Server will be available at `http://localhost:3000/mcp`

3. **OpenAI API Key**:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

## Basic Integration

### Simple Agent with GPG Tools

```python
import asyncio
from agents import Agent
from agents.mcp import MCPServerStreamableHttp

async def main():
    # Connect to the GPG MCP server
    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={
            "url": "http://localhost:3000/mcp",
            "timeout": 30,
            "cache_tools_list": True,
        },
    ) as mcp_server:

        # Create agent with MCP tools
        agent = Agent(
            name="GPG Assistant",
            model="gpt-5",
            instructions="""
            You are a GPG cryptography assistant. You can help users with:
            - Registering new GPG identities
            - Signing text messages
            - Verifying signatures
            - Encrypting messages
            - Decrypting messages
            - Retrieving public keys

            Always explain what you're doing and guide users through GPG operations.
            """,
            mcp_servers=[mcp_server],
        )

        # Run the agent
        result = await agent.run(
            "Register a new user with username 'alice', password 'SecurePass123!', and email 'alice@example.com'"
        )

        print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Configuration

### With Authentication

If your MCP server requires authentication (when deployed to production):

```python
async with MCPServerStreamableHttp(
    name="GPG Webservice",
    params={
        "url": "https://your-domain.com/mcp",
        "headers": {
            "Authorization": "Bearer your-mcp-auth-token",
            "X-API-Key": "your-custom-key",
        },
        "timeout": 30,
        "cache_tools_list": True,
    },
) as mcp_server:
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        mcp_servers=[mcp_server],
    )
```

### With Custom Timeouts and Retry Logic

```python
async with MCPServerStreamableHttp(
    name="GPG Webservice",
    params={
        "url": "http://localhost:3000/mcp",
        "timeout": 60,  # 60 second timeout for long operations
        "cache_tools_list": False,  # Disable caching for dynamic tool discovery
        "max_retry_attempts": 3,
        "retry_backoff_seconds_base": 2,
    },
) as mcp_server:
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        mcp_servers=[mcp_server],
    )
```

## Complete Example: GPG Workflow

```python
import asyncio
from openai_agents_sdk import Agent
from openai_agents_sdk.mcp import MCPServerStreamableHttp

async def gpg_workflow_demo():
    """
    Demonstrates a complete GPG workflow:
    1. Register two users (Alice and Bob)
    2. Alice signs a message
    3. Bob verifies Alice's signature
    4. Bob encrypts a message for Alice
    5. Alice decrypts Bob's message
    """

    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={
            "url": "http://localhost:3000/mcp",
            "timeout": 30,
            "cache_tools_list": True,
        },
    ) as mcp_server:

        agent = Agent(
            name="GPG Workflow Agent",
            model="gpt-4o",
            instructions="""
            You are a GPG expert helping users with cryptographic operations.
            Execute the user's requests step by step and explain what you're doing.
            Store important information like API keys and public keys for later use.
            """,
            mcp_servers=[mcp_server],
        )

        # Step 1: Register Alice
        print("=== Step 1: Registering Alice ===")
        result = await agent.run(
            "Register user 'alice' with password 'AlicePass123!' and email 'alice@example.com'. "
            "Save the API key for later use."
        )
        print(f"Alice registered: {result.output}\n")

        # Step 2: Register Bob
        print("=== Step 2: Registering Bob ===")
        result = await agent.run(
            "Register user 'bob' with password 'BobPass123!' and email 'bob@example.com'. "
            "Save the API key for later use."
        )
        print(f"Bob registered: {result.output}\n")

        # Step 3: Alice signs a message
        print("=== Step 3: Alice Signs a Message ===")
        result = await agent.run(
            "Using Alice's API key, sign the message: 'Hello Bob, this is Alice!'"
        )
        print(f"Message signed: {result.output}\n")

        # Step 4: Get Alice's public key and verify signature
        print("=== Step 4: Bob Verifies Alice's Signature ===")
        result = await agent.run(
            "Get Alice's public key using her API key, then verify the signature "
            "you just created against the original message."
        )
        print(f"Verification result: {result.output}\n")

        # Step 5: Bob encrypts for Alice
        print("=== Step 5: Bob Encrypts a Message for Alice ===")
        result = await agent.run(
            "Using Bob's API key and Alice's public key, encrypt the message: "
            "'Hi Alice, this encrypted message is from Bob!'"
        )
        print(f"Message encrypted: {result.output}\n")

        # Step 6: Alice decrypts Bob's message
        print("=== Step 6: Alice Decrypts Bob's Message ===")
        result = await agent.run(
            "Using Alice's API key, decrypt the encrypted message you just created."
        )
        print(f"Decrypted message: {result.output}\n")

if __name__ == "__main__":
    asyncio.run(gpg_workflow_demo())
```

## Available GPG Tools

The agent will have access to these tools from the MCP server:

| Tool Name | Description | Required Auth |
|-----------|-------------|---------------|
| `register_user` | Register new user with automatic GPG key generation | No |
| `sign_text` | Sign text using user's private GPG key | Yes (API key) |
| `verify_text_signature` | Verify a signature against a public key | No |
| `encrypt_text` | Encrypt text for a recipient | Yes (API key) |
| `decrypt_text` | Decrypt text using user's private key | Yes (API key) |
| `get_user_public_key` | Get user's public GPG key | Yes (API key) |

## Tool Filtering

To expose only specific tools to your agent:

```python
from openai_agents_sdk.mcp import create_static_tool_filter

# Only allow signing and verification
tool_filter = create_static_tool_filter(
    allowed_tools=["sign_text", "verify_text_signature", "get_user_public_key"]
)

async with MCPServerStreamableHttp(
    name="GPG Webservice",
    params={
        "url": "http://localhost:3000/mcp",
        "timeout": 30,
    },
    tool_filter=tool_filter,
) as mcp_server:
    agent = Agent(
        name="Signing Agent",
        model="gpt-4o",
        instructions="You can only sign and verify messages.",
        mcp_servers=[mcp_server],
    )
```

## Hosted MCP (Production)

For production deployments where the MCP server is publicly accessible:

```python
from openai_agents_sdk import HostedMCPTool

# Let OpenAI's infrastructure handle the MCP connection
agent = Agent(
    name="GPG Assistant",
    model="gpt-4o",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "gpg-webservice",
                "server_url": "https://your-domain.com/mcp",
                "require_approval": "never",  # or "always" for user approval
            }
        )
    ],
)
```

## Deployment Checklist

When deploying the MCP server for OpenAI AgentSDK use:

### 1. Configure Environment
```env
# .env
GPG_API_BASE=https://your-gpg-service.com
MCP_PORT=3000
MCP_HOST=0.0.0.0
```

### 2. Start HTTP Server
```bash
npm run build
npm run start:http
```

### 3. Deploy Behind HTTPS
Use nginx/Caddy reverse proxy (see main README.md for nginx config)

### 4. Test Connection
```bash
# Health check
curl https://your-domain.com/health

# Test MCP endpoint
curl -X POST https://your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

### 5. Update Agent Code
```python
async with MCPServerStreamableHttp(
    name="GPG Webservice",
    params={
        "url": "https://your-domain.com/mcp",
        "timeout": 30,
    },
) as mcp_server:
    # Your agent code
```

## Troubleshooting

### Connection Timeout
Increase timeout in MCP params:
```python
params={"url": "...", "timeout": 60}
```

### Tool Discovery Issues
Disable cache to force refresh:
```python
params={"url": "...", "cache_tools_list": False}
```

### Authentication Errors
Ensure API keys are passed correctly to GPG operations:
```python
# Agent will automatically handle this, but you can guide it:
result = await agent.run(
    "Using the API key from the registration, sign this message: 'Hello'"
)
```

### Health Check Failed
Verify server is running:
```bash
curl http://localhost:3000/health
```

## Example Output

```
=== Step 1: Registering Alice ===
Alice registered: Successfully registered user 'alice'.
API Key: gpg_abc123def456... (save this securely!)
Public key fingerprint: A1B2C3D4E5F6...

=== Step 3: Alice Signs a Message ===
Message signed:
Text: "Hello Bob, this is Alice!"
Signature: iQEzBAABCAAdFiEE...
Signature (base64): aVFFekJBQUJDQUFk...

=== Step 4: Bob Verifies Alice's Signature ===
Verification result: ✓ Signature is VALID
Signed by: alice <alice@example.com>
Signature created: 2025-11-17 12:34:56
```

## Resources

- [OpenAI Agent SDK Documentation](https://openai.github.io/openai-agents-python/)
- [MCP Protocol Specification](https://modelcontextprotocol.info/)
- [GPG Webservice MCP README](./README.md)
- [Flask GPG Webservice](https://github.com/dtrog/gpg-webservice)

## Support

For issues with:
- **OpenAI Agent SDK integration**: Open issue in this repository
- **Flask GPG webservice**: See [dtrog/gpg-webservice](https://github.com/dtrog/gpg-webservice)
- **MCP protocol**: See [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk)
