from pydantic import BaseModel, Field
from typing import Literal, Optional, List

# --- 1. The Proposal (from Prime AI) ---
class ProposalMessage(BaseModel):
    id: str = Field(..., description="Unique Proposal ID (e.g., PROP-2025-001)")
    content: str = Field(..., description="The executive action proposed.")
    signature: str = Field(..., description="Prime AI's GPG signature of the content.")

# --- 2. The Vote (from Auditors) ---
class VoteMessage(BaseModel):
    agent_role: Literal["Justiciar", "Sentinel", "Logician", "Historian"]
    proposal_id: str
    phase: Literal["PRE-VOTE", "COMMIT"]
    vote: Literal["AGREE", "DISAGREE"]
    justification: str = Field(..., description="Reference to Codex/Volumina.")
    signature: str = Field(..., description="Auditor's GPG signature of this vote.")

# --- 3. The Verification Result (from ID Agent) ---
class VerificationResult(BaseModel):
    status: Literal["VERIFIED", "FAILED"]
    agent_id: str
    message: str