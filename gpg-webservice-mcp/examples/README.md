# OpenAI Agent SDK Examples

This directory contains example scripts demonstrating how to use the GPG Webservice MCP server with OpenAI's Agent SDK.

## Prerequisites

1. **Python 3.10 or higher**

2. **OpenAI API Key**
   ```bash
   export OPENAI_API_KEY=your-openai-api-key-here
   ```

3. **MCP HTTP Server Running**
   ```bash
   # In the parent directory
   npm run build
   npm run start:http
   ```
   Server should be running at `http://localhost:3000/mcp`

4. **Flask GPG Webservice Running**
   ```bash
   # The backend GPG service should be running at http://localhost:5000
   # See the main GPG webservice repository for setup
   ```

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install openai-agents-sdk
```

## Running the Examples

### Basic Example

The basic example demonstrates:
- Connecting to the MCP server
- Registering a new GPG user
- Signing a message
- Verifying a signature

```bash
python openai_agent_example.py
```

Expected output:
```
🚀 Starting GPG Agent with MCP tools...
============================================================

✅ Agent initialized with GPG tools
📝 Available tools: register_user, sign_text, verify_text_signature,
   encrypt_text, decrypt_text, get_user_public_key
============================================================

🔧 Example 1: Registering a new user...
------------------------------------------------------------

📤 Result:
Successfully registered user 'demo_user' with GPG keys.
API Key: gpg_abc123... (save this securely!)
...
```

## Available Examples

| File | Description |
|------|-------------|
| `openai_agent_example.py` | Basic usage: register, sign, verify |

## Creating Your Own Agent

Here's a minimal template:

```python
import asyncio
from openai_agents_sdk import Agent
from openai_agents_sdk.mcp import MCPServerStreamableHttp

async def main():
    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={
            "url": "http://localhost:3000/mcp",
            "timeout": 30,
        },
    ) as mcp_server:

        agent = Agent(
            name="My GPG Agent",
            model="gpt-4o",
            instructions="Your custom instructions here",
            mcp_servers=[mcp_server],
        )

        result = await agent.run("Your prompt here")
        print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### "Connection refused" error

Make sure the MCP HTTP server is running:
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

### "OPENAI_API_KEY not set" error

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=sk-...
```

### "Failed to fetch function definitions" error

Ensure the Flask GPG webservice is running:
```bash
curl http://localhost:5000/openai/function_definitions
```

### Timeout errors

Increase the timeout in the MCP server params:
```python
params={
    "url": "http://localhost:3000/mcp",
    "timeout": 60,  # Increased to 60 seconds
}
```

## Next Steps

- Read the full integration guide: [OPENAI_AGENT_SDK.md](../OPENAI_AGENT_SDK.md)
- Explore the main README: [README.md](../README.md)
- Check the Flask GPG webservice documentation

## License

MIT
