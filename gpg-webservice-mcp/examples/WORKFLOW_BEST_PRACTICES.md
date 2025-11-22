# OpenAI Agent SDK + MCP: Workflow Best Practices

## Overview

This guide documents best practices for building complex workflows using OpenAI's Agent SDK with Model Context Protocol (MCP) servers.

## Key Learnings

### 1. Context Management is Critical

**Problem**: Agents can lose context between operations, especially API keys and credentials.

**Solutions**:
- Use **explicit memory instructions** in agent prompts
- Store credentials with **clear labels**: `"ALICE_KEY: sk_..."`
- Number items in sequences: `"1. alice: key1, 2. bob: key2"`
- Reinforce storage after each credential retrieval

```python
agent = Agent(
    instructions="""
    CRITICAL: When you receive an API key (starts with 'sk_'),
    ALWAYS store it with format "USERNAME_KEY: <key>" and
    reuse it for subsequent operations.
    """
)
```

### 2. Turn Limits Are Real

**Problem**: Complex workflows can exceed default turn limits (10 turns).

**Solutions**:
- Start with `max_turns=20` for moderate complexity
- Use `max_turns=25-30` for multi-user or multi-phase workflows
- Monitor turn usage: `result.current_turn / result.max_turns`
- Simplify workflows if consistently hitting limits

```python
result = await Runner.run(
    starting_agent=agent,
    input=message,
    max_turns=25  # Adjust based on workflow complexity
)

# Monitor efficiency
if result.current_turn >= result.max_turns - 2:
    print("⚠️  Near turn limit - consider simplifying")
```

### 3. Single Conversation Pattern

**Problem**: Separate `Runner.run()` calls lose all context.

**Solution**: Consolidate entire workflow into ONE conversation.

❌ **Don't do this**:
```python
# Each call loses context
result1 = await Runner.run(agent, "Login as alice")
result2 = await Runner.run(agent, "Sign a message")  # Lost API key!
result3 = await Runner.run(agent, "Verify signature")  # Lost everything!
```

✅ **Do this instead**:
```python
# Single conversation maintains context
workflow = """
1. Login as alice (store API key)
2. Sign message using stored API key
3. Verify signature
"""
result = await Runner.run(agent, workflow, max_turns=20)
```

### 4. Phase-Based Workflows

**Pattern**: Break complex workflows into clear phases with confirmation points.

```python
workflow = """
PHASE 1: Authentication
1. Login alice
2. Store alice's API key as ALICE_KEY
3. Confirm: "Phase 1 complete, have ALICE_KEY"

PHASE 2: Cryptographic Operation
4. Using ALICE_KEY, sign message
5. Store signature as SIGNATURE_1
6. Confirm: "Phase 2 complete, have SIGNATURE_1"

PHASE 3: Verification
7. Verify SIGNATURE_1
8. Report final status
"""
```

### 5. Error Recovery Instructions

**Pattern**: Explicitly teach the agent how to recover from errors.

```python
agent = Agent(
    instructions="""
    ERROR RECOVERY:
    - Login fails → Try register_user
    - Auth error (401) → Get fresh API key via login
    - User not found → Register new user
    - Operation fails → Check you have correct credentials
    
    Always report: "Error: X. Recovery: Y. Result: Z"
    """
)
```

### 6. Multi-User Workflows

**Challenge**: Managing multiple users' credentials simultaneously.

**Best Practices**:
```python
workflow = """
SETUP ALL USERS FIRST:
1. Login alice → Store "1. ALICE_KEY: <key>"
2. Login bob → Store "2. BOB_KEY: <key>"
3. Login charlie → Store "3. CHARLIE_KEY: <key>"
4. Confirm all keys stored

THEN PERFORM OPERATIONS:
5. Use ALICE_KEY for operation A
6. Use BOB_KEY for operation B
7. Use CHARLIE_KEY for operation C
"""
```

**Why**: Getting all credentials upfront prevents "going back" to retrieve them later, which wastes turns.

### 7. Clear Output Formatting

**Pattern**: Request structured output from the agent.

```python
workflow = """
After completing the workflow, provide a summary in this format:

WORKFLOW SUMMARY:
- Phase 1: [Status] - [Details]
- Phase 2: [Status] - [Details]
- Phase 3: [Status] - [Details]

CREDENTIALS USED:
- alice: [API key]
- bob: [API key]

ARTIFACTS CREATED:
- Signature 1: [value]
- Encrypted message: [value]

FINAL STATUS: Success/Failed
"""
```

### 8. Model Selection

**Recommendations**:
- **Simple workflows**: `gpt-4o-mini` (faster, cheaper)
- **Complex workflows**: `gpt-4o` (better context management)
- **Mission critical**: `gpt-4o` with higher `max_turns`

```python
# For complex multi-user workflows
agent = Agent(
    model="gpt-4o",  # Better at maintaining context
    instructions="...",
)

# For simple single-operation tasks  
agent = Agent(
    model="gpt-4o-mini",  # More economical
    instructions="...",
)
```

### 9. Tracing and Debugging

**Always use tracing** for production workflows:

```python
from agents import gen_trace_id, trace

trace_id = gen_trace_id()
with trace(workflow_name="My Workflow", trace_id=trace_id):
    trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
    print(f"View trace: {trace_url}")
    
    result = await Runner.run(agent, workflow)
```

**Benefits**:
- See exact tool calls and responses
- Identify where context is lost
- Measure turn efficiency
- Debug auth and API issues

### 10. Incremental Complexity

**Approach**: Start simple, add complexity gradually.

**Development Path**:
1. **Week 1**: Single operation (login) ✅ `simple_test.py`
2. **Week 2**: Two operations (login + sign) ✅ Basic workflow
3. **Week 3**: Full workflow (login + sign + verify) ✅ `openai_agent_example.py`
4. **Week 4**: Multi-user workflows ✅ `advanced_workflow_example.py`

**Don't jump to step 4** without validating steps 1-3 work reliably.

## Workflow Complexity Guide

| Complexity | Operations | Max Turns | Example |
|------------|------------|-----------|---------|
| Simple | 1-2 | 10-15 | Login, get key |
| Moderate | 3-5 | 15-20 | Login, sign, verify |
| Complex | 6-10 | 20-25 | Multi-user encryption |
| Advanced | 10+ | 25-30 | Signature chains, audit trails |

## Common Pitfalls

### ❌ Pitfall 1: Assuming Context Persists
```python
# Agent forgets API key between operations
result = await Runner.run(agent, "Login")
result = await Runner.run(agent, "Sign message")  # ❌ Lost context
```

### ❌ Pitfall 2: Vague Instructions
```python
workflow = "Do some GPG stuff"  # ❌ Too vague
```

### ❌ Pitfall 3: Not Monitoring Turn Usage
```python
# Workflow silently fails at turn limit
result = await Runner.run(agent, workflow)  # ❌ No limit set
```

### ❌ Pitfall 4: Complex Workflows Without Phases
```python
# Long list of steps with no structure
workflow = "1. Do A, 2. Do B, 3. Do C... 20. Do T"  # ❌ No organization
```

## Testing Strategy

### 1. Unit Test Individual Operations
```python
# test_individual_operations.py
async def test_login():
    result = await Runner.run(agent, "Login as alice")
    assert "api_key" in result.final_output.lower()
```

### 2. Integration Test Complete Workflows
```python
# test_complete_workflow.py
async def test_sign_and_verify():
    workflow = "Login, sign message, verify signature"
    result = await Runner.run(agent, workflow, max_turns=20)
    assert "verified" in result.final_output.lower()
```

### 3. Stress Test Turn Limits
```python
# test_turn_efficiency.py
result = await Runner.run(agent, complex_workflow, max_turns=30)
efficiency = result.current_turn / result.max_turns
assert efficiency < 0.8, "Workflow too close to turn limit"
```

## Production Checklist

Before deploying agent workflows to production:

- [ ] Tested with `max_turns` set 20% higher than typical usage
- [ ] Implemented tracing with `trace()` context manager
- [ ] Added error recovery instructions in agent prompt
- [ ] Validated context persists across all operations
- [ ] Tested with multiple users/concurrent operations
- [ ] Documented expected turn usage for monitoring
- [ ] Added timeout handling for long-running operations
- [ ] Implemented retry logic for transient failures
- [ ] Tested with rate limits (OpenAI API limits)
- [ ] Added logging for debugging production issues

## Performance Optimization

### Reduce Turn Usage

1. **Batch credential retrieval**: Get all API keys first
2. **Clear success criteria**: Define what "done" looks like
3. **Remove unnecessary verifications**: Only verify critical operations
4. **Streamline instructions**: Shorter prompts = faster processing

### Example Optimization

❌ **Before** (18 turns):
```python
workflow = """
Login alice. Confirm login successful.
Get alice's API key. Confirm you have it.
Sign message. Confirm signature created.
Verify signature. Confirm verification passed.
"""
```

✅ **After** (12 turns):
```python
workflow = """
1. Login alice (store API_KEY)
2. Sign message using API_KEY (store SIGNATURE)
3. Verify SIGNATURE
Report: "Complete. Signature verified."
"""
```

## Conclusion

Building complex workflows with OpenAI Agent SDK + MCP requires:
- **Explicit context management** via clear instructions
- **Realistic turn budgets** (20-30 for complex workflows)
- **Single conversation pattern** (no separate Runner.run calls)
- **Phase-based organization** with confirmation points
- **Error recovery instructions** for resilience
- **Tracing and monitoring** for debugging

Start simple, test incrementally, and add complexity gradually.

## Example Files

- `simple_test.py` - Basic single operation
- `openai_agent_example.py` - Standard workflow (login + sign + verify)
- `advanced_workflow_example.py` - Complex multi-user scenarios

## Further Reading

- [OpenAI Agent SDK Docs](https://github.com/openai/openai-agent-sdk-python)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)
- [OpenAI Platform Traces](https://platform.openai.com/traces)
