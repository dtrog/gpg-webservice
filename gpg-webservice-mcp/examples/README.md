# OpenAI Agent SDK Examples

This directory contains **optimized** example scripts demonstrating how to use the GPG Webservice MCP server with OpenAI's Agent SDK for complex workflows.

## 🎯 Quick Start

1. **Simple Test** (verifies connectivity):
   ```bash
   python simple_test.py
   ```

2. **Basic Workflow** (login → sign → verify):
   ```bash
   python openai_agent_example.py
   ```

3. **Advanced Workflows** (multi-user, error recovery):
   ```bash
   python advanced_workflow_example.py
   ```

## Prerequisites

1. **Python 3.10 or higher**

2. **OpenAI API Key**
   ```bash
   export OPENAI_API_KEY=your-openai-api-key-here
   ```

3. **GPG Webservice Running (with Docker)**
   ```bash
   # In the root directory of the project
   docker-compose up -d
   ```
   This starts all three services:
   - REST API: `http://localhost:5555`
   - MCP Server: `http://localhost:3000/mcp`
   - Dashboard: `http://localhost:8080`

   Verify MCP is running:
   ```bash
   curl http://localhost:3000/health
   # Should return: {"status":"healthy",...,"tools_loaded":7}
   ```

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install openai-agents
pip install openai-agents-mcp
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

| File | Purpose | Complexity | Best For |
|------|---------|------------|----------|
| `simple_test.py` | Connectivity test | ⭐ Simple | Debugging, validation |
| `openai_agent_example.py` | **Standard workflow** | ⭐⭐ Moderate | Production basic workflows |
| `streamlined_example.py` | Ultra-reliable workflow | ⭐⭐ Moderate | Critical production workflows |
| `advanced_workflow_example.py` | Complex scenarios | ⭐⭐⭐ Advanced | Learning, multi-user workflows |

## 📚 Documentation

- **[WORKFLOW_BEST_PRACTICES.md](WORKFLOW_BEST_PRACTICES.md)** - Complete guide to building reliable workflows
- **[OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)** - What we optimized and why
- **[IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md)** - Technical implementation details

## Example Descriptions

### `simple_test.py` - Basic Connectivity Test

**Purpose**: Verify MCP server connectivity with minimal complexity

**What it does**:
- Connects to MCP server
- Performs single login operation
- Validates response

**Use when**:
- Testing MCP server setup
- Debugging connection issues
- Validating environment configuration

```bash
python simple_test.py
```

Expected: "Login successful. You can now perform GPG operations..."

### `openai_agent_example.py` - Standard Workflow (OPTIMIZED)

**Purpose**: Production-ready 3-step workflow with best practices

**What it does**:
1. Login or register user (with login-first pattern)
2. Sign a message using stored API key
3. Verify the signature

**Optimizations**:
- ✅ Explicit memory management instructions
- ✅ Error recovery guidance
- ✅ 20 turn limit (increased from 15)
- ✅ Turn usage monitoring
- ✅ Clear step-by-step workflow

**Use when**:
- Building standard GPG workflows
- Need reliable 3-5 step workflows
- Template for new agent implementations

```bash
python openai_agent_example.py
```

**Key Features**:
- Login-first pattern (avoids database pollution)
- Context retention across operations
- Comprehensive error handling
- Execution statistics

### `streamlined_example.py` - Ultra-Reliable Workflow (NEW)

**Purpose**: Maximum reliability through extreme explicitness

**What it does**:
- Same as standard workflow but with explicit state tracking
- Forces agent to confirm storage of all credentials
- Requires status updates after each step

**Special Features**:
- State storage format: `"STORED: NAME = value"`
- Step completion confirmations
- Success indicator analysis
- Higher turn budget (20)

**Use when**:
- Production critical workflows
- Debugging context loss issues
- Need guaranteed state retention
- Maximum reliability required

```bash
python streamlined_example.py
```

### `advanced_workflow_example.py` - Complex Scenarios (NEW)

**Purpose**: Demonstrate advanced patterns and multi-user workflows

**Includes 3 workflows**:

1. **Two-Party Encryption** (25 turns)
   - Setup Alice and Bob
   - Alice encrypts message for Bob
   - Bob decrypts the message
   
2. **Signature Chain** (30 turns)
   - Multiple users sign same document
   - Creates audit trail
   - Verifies all signatures

3. **Error Recovery Demo** (20 turns)
   - Tests error scenarios
   - Demonstrates recovery patterns
   - Shows resilience strategies

**Use when**:
- Learning complex workflow patterns
- Building multi-user systems
- Need error recovery examples
- Researching workflow optimization

```bash
python advanced_workflow_example.py
```

## Available Examples

## Creating Your Own Agent

Here's a minimal template:

```python
import asyncio
from agents import Agent
from agents.mcp import MCPServerStreamableHttp

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
