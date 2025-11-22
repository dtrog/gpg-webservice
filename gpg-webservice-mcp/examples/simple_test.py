#!/usr/bin/env python3
"""Simple test to verify MCP tools work correctly"""

import asyncio
import os
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set")
        return

    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={"url": "http://localhost:3000/mcp"},
    ) as mcp_server:

        agent = Agent(
            name="GPG Assistant",
            model="gpt-4o",
            instructions=(
                "You are a GPG assistant. When you login, extract the "
                "api_key from the response and remember it."
            ),
            mcp_servers=[mcp_server],
        )

        # Simple login test
        print("Testing login...")
        result = await Runner.run(
            starting_agent=agent,
            input=(
                "Login with username 'alice_demo' and password "
                "'SecurePass123!'"
            )
        )
        print(f"\nResult: {result.final_output}\n")


if __name__ == "__main__":
    asyncio.run(main())
