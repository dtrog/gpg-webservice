#!/usr/bin/env python3
"""
Advanced GPG Webservice MCP workflow example

This example demonstrates more complex scenarios:
- Multiple user interactions
- Message encryption/decryption between users
- Error recovery patterns
- State management across operations

Prerequisites:
    pip install openai-agents

Usage:
    1. Start the MCP HTTP server: npm run start:http
    2. Set your OpenAI API key: export OPENAI_API_KEY=your-key
    3. Run this script: python examples/advanced_workflow_example.py
"""

import asyncio
import os
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStreamableHttp


async def two_party_encryption_workflow(mcp_server):
    """
    Demonstrates encryption between two users.
    Alice encrypts a message that only Bob can decrypt.
    """
    print("\n" + "=" * 60)
    print("🔐 TWO-PARTY ENCRYPTION WORKFLOW")
    print("=" * 60)
    
    agent = Agent(
        name="GPG Encryption Assistant",
        model="gpt-4o",
        instructions="""
        You are a GPG encryption expert managing multi-user workflows.
        
        MEMORY MANAGEMENT (CRITICAL):
        - Store ALL API keys with their associated usernames
        - Format: "username: api_key"
        - Keep this data throughout the entire conversation
        
        WORKFLOW APPROACH:
        - Complete each user's setup before moving to the next
        - Always verify you have the required credentials before operations
        - Use descriptive labels when reporting success/failure
        
        ERROR RECOVERY:
        - If you lose an API key, login again to retrieve it
        - If operation fails, check if you're using the correct API key
        - Provide clear status updates at each step
        """,
        mcp_servers=[mcp_server],
    )
    
    workflow = """
    Execute this secure communication workflow:
    
    PHASE 1: Setup Alice
    1. Login or register user 'alice_secure' with password 'AlicePass456!'
    2. Store Alice's API key with label "ALICE_KEY: <key>"
    
    PHASE 2: Setup Bob  
    3. Login or register user 'bob_secure' with password 'BobPass789!'
    4. Store Bob's API key with label "BOB_KEY: <key>"
    5. Get Bob's public key and store it with label "BOB_PUBLIC_KEY: <key>"
    
    PHASE 3: Secure Message
    6. Using ALICE_KEY, encrypt this message for Bob:
       "Secret meeting at 3pm tomorrow. Project Phoenix is go."
    7. Store the encrypted message as "ENCRYPTED_MSG: <ciphertext>"
    
    PHASE 4: Verification
    8. Using BOB_KEY, decrypt the message from step 6
    9. Confirm the decrypted message matches the original
    
    After each phase, confirm completion before proceeding.
    Use clear labels so credentials don't get mixed up.
    """
    
    print("📋 Executing multi-phase encryption workflow...")
    print("⏱️  This may take several turns...")
    
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=workflow,
            max_turns=25  # Complex workflow needs more turns
        )
        
        print("\n" + "=" * 60)
        print("✅ WORKFLOW COMPLETED")
        print("=" * 60)
        print(result.final_output)
        
        if hasattr(result, 'current_turn'):
            efficiency = (result.current_turn / result.max_turns) * 100
            print(f"\n📊 Stats: {result.current_turn}/{result.max_turns} turns ({efficiency:.0f}% of limit)")
            
            if result.current_turn >= result.max_turns - 2:
                print("⚠️  Warning: Workflow used near-max turns.")
                print("   Consider simplifying or increasing max_turns.")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        print("\n💡 Common issues:")
        print("   - Workflow too complex for turn limit")
        print("   - Agent lost context between steps")
        print("   - MCP server connection issues")
        raise


async def signature_chain_workflow(mcp_server):
    """
    Demonstrates a chain of signed messages.
    Multiple users sign messages, creating an audit trail.
    """
    print("\n" + "=" * 60)
    print("🔗 SIGNATURE CHAIN WORKFLOW")
    print("=" * 60)
    
    agent = Agent(
        name="GPG Signature Chain Manager",
        model="gpt-4o",
        instructions="""
        You manage a signature chain for document approval workflows.
        
        CRITICAL MEMORY RULES:
        - Maintain a numbered list of all API keys: "1. user1: key1, 2. user2: key2"
        - Store each signature immediately after creation
        - Keep track of the message being signed (it's the same for all)
        
        WORKFLOW PATTERN:
        - Get credentials for ALL users first
        - Then perform signing operations in sequence
        - Verify each signature before creating the next
        - Build a complete audit trail
        
        OUTPUT FORMAT:
        - Report each signature with format: "USER signed at STEP"
        - Final output should list the complete chain
        """,
        mcp_servers=[mcp_server],
    )
    
    workflow = """
    Create a document approval signature chain:
    
    SETUP PHASE:
    1. Login/register these users (store their API keys):
       - 'manager_alice' password 'ManagerPass1!'
       - 'reviewer_bob' password 'ReviewerPass2!'
       - 'approver_charlie' password 'ApproverPass3!'
    
    SIGNING PHASE:
    2. Have manager_alice sign: "Budget approval for Q1 2025: $500,000"
    3. Verify alice's signature
    4. Have reviewer_bob sign the SAME message
    5. Verify bob's signature
    6. Have approver_charlie sign the SAME message
    7. Verify charlie's signature
    
    FINAL REPORT:
    8. List all three signatures showing the complete approval chain
    
    Keep all signatures in memory to show the complete chain at the end.
    """
    
    print("📋 Building signature chain with multiple approvers...")
    
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=workflow,
            max_turns=30  # Signature chain is complex
        )
        
        print("\n" + "=" * 60)
        print("✅ SIGNATURE CHAIN COMPLETED")
        print("=" * 60)
        print(result.final_output)
        
        if hasattr(result, 'current_turn'):
            print(f"\n📊 Chain built in {result.current_turn} turns")
        
    except Exception as e:
        print(f"\n❌ Chain building failed: {e}")
        raise


async def error_recovery_demo(mcp_server):
    """
    Demonstrates error handling and recovery patterns.
    """
    print("\n" + "=" * 60)
    print("🔄 ERROR RECOVERY DEMONSTRATION")
    print("=" * 60)
    
    agent = Agent(
        name="GPG Error Recovery Assistant",
        model="gpt-4o",
        instructions="""
        You demonstrate robust error handling in GPG operations.
        
        ERROR HANDLING STRATEGY:
        - Always check if operations succeed
        - If auth fails, re-authenticate before retrying
        - If user not found, register them
        - Log each error and recovery attempt
        
        RECOVERY PATTERNS:
        1. Login fails → Register new user
        2. Auth error → Get fresh API key
        3. Invalid signature → Verify you have correct public key
        4. Encryption fails → Confirm recipient public key exists
        
        Report both the error AND the recovery action taken.
        """,
        mcp_servers=[mcp_server],
    )
    
    workflow = """
    Demonstrate error recovery patterns:
    
    TEST 1: User doesn't exist
    - Try to login as 'new_user_test' with password 'TestPass1!'
    - When it fails, register the user
    - Then login successfully
    
    TEST 2: Using invalid credentials
    - Try signing a message before logging in (should fail)
    - Detect the auth error
    - Login with 'new_user_test' from TEST 1
    - Retry signing successfully
    
    TEST 3: Recovery verification
    - Sign message: "Recovery test successful"
    - Verify the signature
    - Confirm the complete workflow succeeded
    
    Report each error encountered and how you recovered from it.
    """
    
    print("📋 Testing error scenarios and recovery...")
    
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=workflow,
            max_turns=20
        )
        
        print("\n" + "=" * 60)
        print("✅ ERROR RECOVERY DEMO COMPLETED")
        print("=" * 60)
        print(result.final_output)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Note: Some failures are expected in this demo!")
        raise


async def main():
    """Run all advanced workflow examples."""
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY=your-api-key-here")
        return
    
    print("🚀 ADVANCED GPG WORKFLOWS WITH MCP")
    print("=" * 60)
    print("This demo shows complex multi-user scenarios and error handling")
    print("=" * 60)
    
    async with MCPServerStreamableHttp(
        name="GPG Webservice",
        params={"url": "http://localhost:3000/mcp"},
    ) as mcp_server:
        
        trace_id = gen_trace_id()
        with trace(workflow_name="Advanced GPG Workflows", trace_id=trace_id):
            trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
            print(f"\n📊 View trace: {trace_url}")
            
            # Run workflows
            print("\n" + "=" * 60)
            print("WORKFLOW 1 OF 3")
            await two_party_encryption_workflow(mcp_server)
            
            print("\n\n" + "=" * 60)
            print("WORKFLOW 2 OF 3")
            await signature_chain_workflow(mcp_server)
            
            print("\n\n" + "=" * 60)
            print("WORKFLOW 3 OF 3")
            await error_recovery_demo(mcp_server)
    
    print("\n" + "=" * 60)
    print("✨ ALL ADVANCED WORKFLOWS COMPLETED!")
    print("=" * 60)
    print("\n📝 Summary:")
    print("  ✅ Two-party encryption/decryption")
    print("  ✅ Multi-party signature chains")
    print("  ✅ Error recovery patterns")
    print("\n💡 These patterns can be adapted for your use cases")


if __name__ == "__main__":
    asyncio.run(main())
