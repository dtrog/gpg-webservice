#!/usr/bin/env python3
"""
Example of using GPG Webservice MCP with OpenAI Agent SDK

This example demonstrates how to:
- Connect to a local MCP server via Streamable HTTP
- Use GPG cryptographic operations through MCP tools
- Register users, sign messages, and verify signatures

Prerequisites:
    pip install openai-agents

Usage:
    1. Start the MCP HTTP server: npm run start:http
    2. Set your OpenAI API key: export OPENAI_API_KEY=your-key
    3. Run this script: python examples/openai_agent_example.py
"""

import asyncio
import os
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStreamableHttp


async def run(mcp_server):
    """Run GPG cryptography examples using the MCP server."""
    
    # Create agent with GPG tools
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        instructions="""
        You are a helpful GPG cryptography assistant.
        
        CRITICAL: When you receive an API key (starts with 'sk_'),
        ALWAYS store it in your working memory and reuse it for
        subsequent operations in the same conversation.
        
        Available operations:
        - login: Authenticate existing users (returns API key)
        - register_user: Create new users with GPG key pairs
        - sign_text: Sign messages (requires API key)
        - verify_text_signature: Verify signatures
        - encrypt_text: Encrypt messages (requires recipient's public key)
        - decrypt_text: Decrypt messages (requires API key)
        - get_user_public_key: Retrieve public keys
        
        Workflow best practices:
        1. Try login FIRST - only register if login explicitly fails
        2. After login/register, REMEMBER the returned API key
        3. Use the API key for ALL authenticated operations
        4. If an operation fails with auth error, retrieve the API key again
        5. Explain each step clearly to the user
        
        Error handling:
        - If login fails with "user not found", then register
        - If any operation fails with "unauthorized", get a fresh API key
        - Always report errors clearly with actionable next steps
        """,
        mcp_servers=[mcp_server],
    )

    print("\n✅ Agent initialized with GPG tools")
    print("📝 Available tools: register_user, login, sign_text,")
    print("   verify_text_signature, encrypt_text, decrypt_text,")
    print("   get_user_public_key")
    print(f"🤖 Model: {agent.model}")
    print(f"🔧 MCP Server: {mcp_server.name}")
    print("=" * 60)

    # Combined workflow in a single conversation
    print("\n🔧 Running complete GPG workflow...")
    print("-" * 60)

    message = (
        "Complete this GPG workflow:\n\n"
        "1. Try to LOGIN first with:\n"
        "   - username: 'alice_demo'\n"
        "   - password: 'SecurePass123!'\n"
        "   If login fails because user doesn't exist, THEN register them.\n\n"
        "2. After step 1, you will have an API key (sk_...).\n"
        "   Store it in memory for the next steps.\n\n"
        "3. Using the API key from step 2, SIGN this message:\n"
        "   'Hello from OpenAI Agent SDK with MCP!'\n\n"
        "4. VERIFY the signature you just created.\n"
        "   Use alice_demo's public key to verify it.\n\n"
        "Important: Keep the API key from step 1 in your working memory "
        "and reuse it for steps 3 and 4. After each step, confirm success "
        "before proceeding."
    )
    print("📋 Task: Complete GPG workflow (login/register → sign → verify)")
    print("⏱️  Max turns: 20 (increased for reliability)")
    
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=message,
            max_turns=20  # Increased for complex workflows
        )
        
        print("\n" + "=" * 60)
        print("📤 WORKFLOW RESULT")
        print("=" * 60)
        print(result.final_output)
        
        # Show execution statistics
        if hasattr(result, 'current_turn'):
            print(f"\n📊 Turns used: {result.current_turn}/{result.max_turns}")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   - Ensure MCP server is running: npm run start:http")
        print("   - Check Flask backend is running: docker-compose up")
        print("   - Verify OPENAI_API_KEY is set correctly")
        print("   - Try running simple_test.py first to verify connectivity")
        raise


async def main():
    """Main entry point for the GPG MCP example."""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY=your-api-key-here")
        return

    print("🚀 Starting GPG Agent with MCP tools...")
    print("=" * 60)

    # Connect to the GPG MCP server running locally
    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={
            "url": "http://localhost:3000/mcp",
        },
    ) as mcp_server:
        # Generate a trace ID for monitoring in OpenAI Platform
        trace_id = gen_trace_id()
        
        trace_name = "GPG Webservice MCP Example"
        with trace(workflow_name=trace_name, trace_id=trace_id):
            trace_url = (
                f"https://platform.openai.com/traces/trace?"
                f"trace_id={trace_id}"
            )
            print(f"📊 View trace: {trace_url}\n")
            await run(mcp_server)

    print("\n" + "=" * 60)
    print("✨ Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
