# OpenAI Agent SDK Implementation Notes

## What Was Implemented

We've implemented an OpenAI Agent SDK example following the patterns from the official `openai-agents-python` repository.

### Key Files

1. **openai_agent_example.py** - Main example script demonstrating:
   - Connecting to GPG Webservice MCP via Streamable HTTP
   - Registering users and managing GPG keys
   - Signing and verifying messages
   - Encrypting and decrypting data
   - Using OpenAI's tracing features

2. **README.md** - Updated with comprehensive documentation:
   - Prerequisites and setup instructions
   - How to run the example
   - Understanding Streamable HTTP vs Hosted MCP
   - Troubleshooting guide

### Implementation Pattern

The example follows OpenAI's recommended MCP integration pattern:

```python
# 1. Connect to MCP server
async with MCPServerStreamableHttp(
    name="GPG Webservice",
    params={"url": "http://localhost:3000/mcp"},
) as mcp_server:

    # 2. Create agent with MCP tools
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        instructions="...",
        mcp_servers=[mcp_server],  # GPG tools automatically discovered
    )

    # 3. Run tasks with tracing
    trace_id = gen_trace_id()
    with trace(workflow_name="GPG Example", trace_id=trace_id):
        result = await Runner.run(starting_agent=agent, input="...")
        print(result.final_output)
```

## Why Streamable HTTP Instead of Hosted MCP?

The official `examples/hosted_mcp` directory shows examples using `HostedMCPTool`, which is for **publicly accessible** MCP servers that OpenAI's infrastructure calls directly.

Our GPG Webservice runs locally (or in Docker), so we use `MCPServerStreamableHttp`:

### Streamable HTTP (Our Implementation)

- **Location**: MCP server runs locally or in private network
- **Flow**: OpenAI → Your Python script → MCP server → Flask API
- **Control**: Full control over tool execution
- **Use case**: Local development, private services

### Hosted MCP (Not Used)

- **Location**: MCP server is publicly accessible via HTTPS
- **Flow**: OpenAI → Public MCP server (no your code involved)
- **Control**: OpenAI handles all tool calls
- **Use case**: Public services like gitmcp.io

## Architecture

```plaintext
┌─────────────────┐
│  User's Python  │
│  Script with    │
│  OpenAI Agent   │
│  SDK            │
└────────┬────────┘
         │
         │ MCPServerStreamableHttp
         │ http://localhost:3000/mcp
         │
         ▼
┌─────────────────┐
│  MCP Server     │
│  (TypeScript)   │
│  Port 3000      │
└────────┬────────┘
         │
         │ HTTP REST API calls
         │ http://localhost:5555
         │
         ▼
┌─────────────────┐
│  Flask REST API │
│  (Python)       │
│  Port 5555      │
└────────┬────────┘
         │
         │ GPG operations
         │
         ▼
┌─────────────────┐
│  GPG Backend    │
│  (gnupg)        │
└─────────────────┘
```

## Testing the Example

### Prerequisites

1. Docker services running:

   ```bash
   docker-compose up -d
   ```

2. MCP server healthy:

   ```bash
   curl http://localhost:3000/health
   # {"status":"healthy",...,"tools_loaded":7}
   ```

3. OpenAI API key set:

   ```bash
   export OPENAI_API_KEY=sk-...
   ```

### Run

```bash
cd gpg-webservice-mcp/examples
pip install openai-agents
python openai_agent_example.py
```

### Expected Results

- Agent registers user `alice_demo`
- Receives API key starting with `sk_`
- Signs message successfully
- Verifies signature
- Encrypts and decrypts data

### Monitoring
View traces at:
`https://platform.openai.com/traces/trace?trace_id=<id>`

## What's Next?

### Potential Enhancements

1. **Streaming Example**: Demonstrate `Runner.run_streamed()` for real-time updates
2. **Multi-User Example**: Show handling multiple users in one session
3. **Error Recovery**: Demonstrate handling failed operations
4. **Advanced Workflows**: Key rotation, revocation, multiple recipients
5. **Custom Authentication**: Show integration with existing auth systems

### Deployment Considerations

1. **Production Setup**: Deploy MCP server with proper HTTPS
2. **Rate Limiting**: Add rate limits to prevent API abuse
3. **Monitoring**: Integrate with logging/monitoring systems
4. **Security**: Environment-based configuration, secrets management

## References

- OpenAI Agent SDK: https://github.com/openai/openai-agents-python
- MCP Specification: https://modelcontextprotocol.io/
- OpenAI MCP Examples: https://github.com/openai/openai-agents-python/tree/main/examples/mcp
- GPG Webservice REST API: ../gpg-webservice-rest/README.md
