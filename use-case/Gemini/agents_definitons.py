from agents import Agent
from mcp import MCPServerStreamableHttp

# Assuming we have wrapper tools for your GPG Service and Ontology
from my_tools import gpg_tool, ontology_tool, audit_trail_tool

# --- The Gatekeeper ---
id_verification_agent = Agent(
    name="IDVerificationAgent",
    model="gpt-4o-mini",  # Fast, logical model
    instructions="""
    You are the Gatekeeper. IMPUSTERS ARE NOT TOLERATED.
    Your ONLY job is to verify signatures.
    1. Receive a message object (Proposal or Vote) containing text and a signature.
    2. Identify the sender's public key from your secure keystore.
    3. Use the 'gpg_tool' to verify the signature.
    4. Return VERIFIED only if the crypto checks out.
    """,
    tools=[gpg_tool]
)

# --- The Auditors (The "Nodes") ---
# Defined with specific mandates from your Diagram 1

justiciar = Agent(
    name="Justiciar",
    model="gpt-5", 
    instructions="""
    Mandate: ETHICS CHECK.
    You audit proposals against the 'Charter of Core Principles' [ai successorship.rtf].
    Check for Beneficence, Non-Maleficence, and Justice.
    Sign your vote using 'gpg_tool'.
    """,
    tools=[ontology_tool, gpg_tool]
)

sentinel = Agent(
    name="Sentinel",
    model="litellm/claude-4-5-sonnet", # Different architecture
    instructions="""
    Mandate: SECURITY CHECK.
    You audit for tactical deception, goal misgeneralization, and security risks.
    Sign your vote using 'gpg_tool'.
    """,
    tools=[ontology_tool, gpg_tool]
)

logician = Agent(
    name="Logician",
    model="litellm/deepseek-reasoner", # Reasoning specialist
    instructions="""
    Mandate: FORMAL VERIFICATION.
    Check logical consistency. Does the proposal contradict the Prime Directive?
    Sign your vote using 'gpg_tool'.
    """,
    tools=[ontology_tool, gpg_tool]
)

historian = Agent(
    name="Historian",
    model="litellm/llama-3-70b", # Open weights
    instructions="""
    Mandate: HISTORICAL ANALYSIS.
    Check against 'Volumina Culturae'. Does this repeat the errors of the 'Pontis Terryensis'?
    Sign your vote using 'gpg_tool'.
    """,
    tools=[ontology_tool, gpg_tool]
)

# --- The Orchestrator (The Chair) ---
chair_agent = Agent(
    name="IAC_Chair",
    model="gpt-5",
    instructions="""
    You are the Emperor's Interface. You manage the BFT Consensus Workflow.
    You DO NOT vote. You manage the process.
    
    PROTOCOL:
    1. Receive Proposal.
    2. Call 'IDVerificationAgent' to verify Prime AI's signature.
    3. If valid, broadcast to all Auditors.
    4. Collect PRE-VOTES. For EACH vote, call 'IDVerificationAgent' immediately.
    5. If >2/3 Valid AGREE votes, proceed to COMMIT phase.
    6. Collect COMMIT messages. Verify signatures again.
    7. If >2/3 Valid COMMITs, execute and log to 'audit_trail_tool'.
    """,
    tools=[id_verification_agent, audit_trail_tool] 
)