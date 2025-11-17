#!/usr/bin/env python3
"""
Simple example of using GPG Webservice MCP with OpenAI Agent SDK

Prerequisites:
    pip install openai-agents-sdk

Usage:
    1. Start the MCP HTTP server: npm run start:http
    2. Set your OpenAI API key: export OPENAI_API_KEY=your-key
    3. Run this script: python examples/openai_agent_example.py
"""

import asyncio
import os
from openai_agents_sdk import Agent
from openai_agents_sdk.mcp import MCPServerStreamableHttp


async def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY=your-api-key-here")
        return

    print("🚀 Starting GPG Agent with MCP tools...")
    print("=" * 60)

    # Connect to the GPG MCP server
    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={
            "url": "http://localhost:3000/mcp",
            "timeout": 30,
            "cache_tools_list": True,
        },
    ) as mcp_server:

        # Create agent with GPG tools
        agent = Agent(
            name="GPG Assistant",
            model="gpt-4o",
            instructions="""
            You are a helpful GPG cryptography assistant. You can:
            - Register new users with GPG key pairs
            - Sign messages with private keys
            - Verify signatures
            - Encrypt and decrypt messages
            - Retrieve public keys

            Always explain what you're doing in simple terms.
            When you register a user, remember their API key for future operations.
            """,
            mcp_servers=[mcp_server],
        )

        print("\n✅ Agent initialized with GPG tools")
        print("📝 Available tools: register_user, sign_text, verify_text_signature,")
        print("   encrypt_text, decrypt_text, get_user_public_key")
        print("=" * 60)

        # Example 1: Register a user
        print("\n🔧 Example 1: Registering a new user...")
        print("-" * 60)

        result = await agent.run(
            "Register a new user with username 'demo_user', "
            "password 'DemoPass123!', and email 'demo@example.com'. "
            "Save the API key for later use."
        )

        print(f"\n📤 Result:\n{result.output}")

        # Example 2: Sign a message
        print("\n🔧 Example 2: Signing a message...")
        print("-" * 60)

        result = await agent.run(
            "Using the API key you just saved, sign this message: "
            "'Hello from OpenAI Agent SDK with MCP!'"
        )

        print(f"\n📤 Result:\n{result.output}")

        # Example 3: Get public key and verify
        print("\n🔧 Example 3: Verifying the signature...")
        print("-" * 60)

        result = await agent.run(
            "Get the public key for the user you just registered, "
            "then verify the signature you just created."
        )

        print(f"\n📤 Result:\n{result.output}")

        print("\n" + "=" * 60)
        print("✨ Demo completed successfully!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
