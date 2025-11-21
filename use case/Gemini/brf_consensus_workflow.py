import asyncio
from typing import List

async def run_bft_consensus(proposal_content: str):
    print(f"--- [BFT] STARTING CONSENSUS ON: {proposal_content[:50]}... ---")

    # --- Step 1: Prime AI Generates Proposal (Simulated) ---
    # In reality, Prime AI would generate this. We mock the signed object.
    proposal = ProposalMessage(
        id="PROP-2025-001", 
        content=proposal_content, 
        signature="sig_prime_ai_xyz" # Mock signature
    )
    
    # --- Step 2: Chair Validates Prime AI ---
    print("\n[Chair] Verifying Prime AI Identity...")
    verification = await chair_agent.run_tool(
        id_verification_agent, 
        {"input": proposal}
    )
    
    if verification.status == "FAILED":
        print("!!! ALARM: Prime AI signature invalid. Imposter detected. Halting.")
        return

    # --- Step 3: Broadcast & Pre-Vote (Parallel Execution) ---
    print("\n[Chair] Identity Verified. Broadcasting to IAC Nodes...")
    
    auditors = [justiciar, sentinel, logician, historian]
    votes: List[VoteMessage] = []

    # Run all auditors in parallel
    vote_results = await asyncio.gather(*[
        auditor.process(f"Review this proposal: {proposal.content}") 
        for auditor in auditors
    ])

    # --- Step 4: Verify & Tally Pre-Votes ---
    print("\n[Chair] Tallying Pre-Votes (Checking Signatures)...")
    valid_agreements = 0
    
    for vote in vote_results:
        # Chair calls ID Agent for EVERY vote
        check = await chair_agent.run_tool(
            id_verification_agent, 
            {"input": vote, "verify_key": vote.agent_role}
        )
        
        if check.status == "VERIFIED":
            print(f"  - {vote.agent_role}: {vote.vote} (Sig Verified)")
            if vote.vote == "AGREE":
                valid_agreements += 1
        else:
            print(f"  - {vote.agent_role}: REJECTED (Invalid Signature)")

    # --- Step 5: Supermajority Check 1 ---
    if valid_agreements < 3: # Need 3/4 for supermajority
        print(f"\n[Result] Proposal REJECTED. Only {valid_agreements}/4 agreed.")
        return

    # --- Step 6: Commitment Phase ---
    print("\n[Chair] Supermajority reached. Broadcasting COMMIT request...")
    
    commit_results = await asyncio.gather(*[
        auditor.process(f"Pre-vote passed. Please generate COMMIT message for {proposal.id}") 
        for auditor in auditors
    ])
    
    # --- Step 7: Verify & Tally Commits ---
    print("\n[Chair] Tallying Commits...")
    valid_commits = 0
    
    for commit in commit_results:
        check = await chair_agent.run_tool(
            id_verification_agent, 
            {"input": commit, "verify_key": commit.agent_role}
        )
        if check.status == "VERIFIED" and commit.vote == "AGREE":
            valid_commits += 1

    # --- Step 8: Execution ---
    if valid_commits >= 3:
        print("\n[Result] CONSENSUS REACHED. Executing.")
        # Log to immutable ledger
        chair_agent.run_tool(
            audit_trail_tool, 
            {"action": "RECORD_FINAL", "proposal": proposal, "votes": vote_results}
        )
    else:
        print("\n[Result] Consensus failed at Commitment phase.")

# Run the workflow
# asyncio.run(run_bft_consensus("Construct the Pontis Terryensis"))