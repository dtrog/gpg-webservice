#!/usr/bin/env python3
"""
Streamlined GPG workflow - optimized for reliability

This version uses extremely explicit instructions and simplified workflow
to maximize success rate within turn limits.

Prerequisites:
    pip install openai-agents

Usage:
    1. Start the MCP HTTP server: npm run start:http
    2. Set your OpenAI API key: export OPENAI_API_KEY=your-key
    3. Run this script: python examples/streamlined_example.py
"""

import asyncio
import os
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStreamableHttp


async def run_streamlined_workflow(mcp_server):
    """Highly optimized workflow with explicit state management."""
    
    agent = Agent(
        name="GPG Assistant",
        model="gpt-4o",
        instructions="""
        You are a GPG cryptography assistant. Follow instructions exactly.
        
        STATE MANAGEMENT RULES (CRITICAL):
        After EVERY operation that returns an API key or creates data:
        1. Immediately store it with this EXACT format: "STORED: <name> = <value>"
        2. Confirm storage by repeating: "Confirmed: I have stored <name>"
        3. Before using stored data, state: "Using stored <name> = <value>"
        
        OPERATION SEQUENCE:
        Step A: Login/register → Store API key → Confirm storage
        Step B: Sign message → Use stored API key → Store signature → Confirm
        Step C: Verify → Use stored signature → Report result
        
        After each step, output: "STEP X COMPLETE. Status: <success/fail>"
        
        ERROR HANDLING:
        - If login fails: Try register_user with same credentials
        - If auth fails: State "Auth failed, need to re-login"
        - If you lose data: State "Lost <name>, need to retrieve again"
        
        Be extremely explicit about what you're storing and using.
        """,
        mcp_servers=[mcp_server],
    )
    
    print("\n✅ Agent initialized")
    print("🎯 Workflow: Login → Sign → Verify")
    print("=" * 60)
    
    # Ultra-explicit workflow
    workflow = """
Execute this workflow with EXPLICIT state management:

STEP 1: AUTHENTICATION
Action: Call login with username='alice_demo', password='SecurePass123!'
Expected: You will receive an API key starting with 'sk_'
Required output: "STORED: API_KEY = sk_..."
If login fails with "user not found":
  - Call register_user with same credentials
  - Expected: You will receive an API key
  - Required output: "STORED: API_KEY = sk_..."
End with: "STEP 1 COMPLETE. Status: success"

STEP 2: SIGN MESSAGE
Action: Call sign_text with:
  - api_key = <use the API_KEY you stored in STEP 1>
  - text = "Hello from OpenAI Agent SDK with MCP!"
Expected: You will receive a signature (long PGP text block)
Required output: 
  - "Using stored API_KEY = sk_..."
  - "STORED: SIGNATURE = <the signature text>"
End with: "STEP 2 COMPLETE. Status: success"

STEP 3: VERIFY SIGNATURE
Action: Get alice_demo's public key, then verify the signature
Required:
  - First: Call get_user_public_key for username='alice_demo'
  - Then: Call verify_text_signature with the public key and SIGNATURE from STEP 2
Required output:
  - "Using stored SIGNATURE = <sig>"
  - "STORED: VERIFIED_RESULT = <true/false>"
End with: "STEP 3 COMPLETE. Status: success"

FINAL OUTPUT:
Summarize:
- API Key: <first 10 chars>
- Signature: <first 50 chars>
- Verification: <true/false>
- Overall: SUCCESS or FAILED
"""
    
    print("📋 Executing streamlined workflow...")
    print("⏱️  Max turns: 20\n")
    
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=workflow,
            max_turns=20
        )
        
        print("\n" + "=" * 60)
        print("📤 WORKFLOW RESULT")
        print("=" * 60)
        print(result.final_output)
        
        if hasattr(result, 'current_turn'):
            efficiency = (result.current_turn / result.max_turns) * 100
            print(f"\n📊 Efficiency: {result.current_turn}/{result.max_turns} turns ({efficiency:.0f}%)")
            
            if result.current_turn < 15:
                print("✅ Excellent efficiency")
            elif result.current_turn < 18:
                print("✓ Good efficiency")
            else:
                print("⚠️  High turn usage - workflow may be too complex")
        
        # Analyze output for success indicators
        output_lower = result.final_output.lower()
        success_indicators = [
            "step 1 complete" in output_lower,
            "step 2 complete" in output_lower,
            "step 3 complete" in output_lower,
            "success" in output_lower or "verified" in output_lower,
        ]
        
        completed_steps = sum(success_indicators)
        print(f"\n✓ Steps completed: {completed_steps}/3")
        
        if completed_steps == 3:
            print("🎉 Full workflow completed successfully!")
        elif completed_steps >= 1:
            print("⚠️  Partial completion - some steps may have failed")
        else:
            print("❌ Workflow appears to have failed")
        
    except Exception as e:
        print(f"\n❌ Workflow exception: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check MCP server: npm run start:http")
        print("   2. Check Flask backend: docker-compose ps")
        print("   3. Try simple_test.py first")
        print("   4. Check OpenAI API key is valid")
        raise


async def main():
    """Main entry point."""
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set")
        print("Run: export OPENAI_API_KEY=your-api-key")
        return
    
    print("🚀 STREAMLINED GPG WORKFLOW")
    print("=" * 60)
    print("Optimized for maximum reliability and clarity")
    print("=" * 60)
    
    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={"url": "http://localhost:3000/mcp"},
    ) as mcp_server:
        
        trace_id = gen_trace_id()
        with trace(workflow_name="Streamlined GPG Workflow", trace_id=trace_id):
            trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
            print(f"\n📊 Trace: {trace_url}")
            
            await run_streamlined_workflow(mcp_server)
    
    print("\n" + "=" * 60)
    print("✨ Workflow execution complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
