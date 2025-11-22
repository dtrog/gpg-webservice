import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
import time

# Assuming these are available via your MCP integration
from openai_agents import Agent, RunContext
from openai_agents.mcp import MCPServerStreamableHttp

class VoteType(Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"

class ConsensusPhase(Enum):
    PRE_VOTE = "PRE_VOTE"
    COMMIT = "COMMIT"

@dataclass
class SignedMessage:
    """Cryptographically signed message using GPG"""
    content: str
    signature: str
    signer_identity: str  # GPG key fingerprint
    timestamp: float

@dataclass
class BFTProposal:
    proposal_id: str
    content: str
    proposer: str  # "Prime_AI" or auditor name
    signature: SignedMessage

@dataclass
class BFTVote:
    proposal_id: str
    voter: str  # auditor role
    phase: ConsensusPhase
    vote: VoteType
    justification: str
    signature: SignedMessage

class IDVerificationAgent:
    """Gatekeeper for cryptographic identity verification using GPG MCP"""
    
    def __init__(self, gpg_mcp_server):
        self.gpg_mcp_server = gpg_mcp_server
        self.agent = Agent(
            name="ID_Verification_Agent",
            model="gpt-4o-mini",  # Fast, deterministic verification
            instructions="""
            YOU ARE THE GATEKEEPER. Your sole purpose is cryptographic identity verification.
            
            CRITICAL RULES:
            1. Verify EVERY signature using GPG tools before accepting any message
            2. Reject ANY message with invalid or missing signatures immediately
            3. Maintain zero tolerance for cryptographic failures
            4. Log all verification attempts for audit purposes
            
            Verification Process:
            - Extract message content and signature
            - Use GPG verify_text_signature tool with the signer's public key
            - Return VERIFIED only if cryptographic proof is valid
            - Return FAILED for any cryptographic failure
            
            No exceptions. No overrides. Cryptographic truth only.
            """,
            mcp_servers=[gpg_mcp_server],
        )
    
    async def verify_signature(self, message: str, signature: str, expected_signer: str) -> bool:
        """Verify a GPG signature against expected signer identity"""
        try:
            result = await self.agent.run(
                f"Verify this signature for expected signer {expected_signer}:\n"
                f"Message: {message}\n"
                f"Signature: {signature}\n"
                "Use verify_text_signature tool with strict validation."
            )
            
            # Parse verification result from GPG tool response
            verification_text = str(result.output).lower()
            return ("valid" in verification_text and 
                    "signature" in verification_text and
                    expected_signer.lower() in verification_text)
                    
        except Exception as e:
            print(f"❌ Signature verification failed for {expected_signer}: {e}")
            return False

class BFTChairAgent:
    """Orchestrates Byzantine Fault Tolerant consensus protocol"""
    
    def __init__(self, verification_agent: IDVerificationAgent, auditors: Dict):
        self.verification_agent = verification_agent
        self.auditors = auditors
        self.consensus_history = []
        
        self.agent = Agent(
            name="BFT_Chair_Agent",
            model="gpt-4o",  # Strategic oversight capabilities
            instructions="""
            You are the BFT Consensus Chair for the Atlantean Governance Framework.
            
            PROTOCOL RULES:
            1. Verify Prime AI signature before processing any proposal
            2. Require supermajority (≥2/3) for both PRE_VOTE and COMMIT phases
            3. Reject any unverified votes immediately
            4. Maintain immutable audit trail of all consensus actions
            
            Byzantine Fault Tolerance:
            - Assume up to f malicious nodes in 3f+1 system
            - Verify every message cryptographically
            - Continue consensus with honest majority
            
            Process Flow:
            Phase 1: Proposal Verification → Broadcast → Pre-Vote Collection
            Phase 2: Supermajority Check → Commit Collection → Final Execution
            """,
        )
    
    async def execute_consensus(self, proposal: BFTProposal) -> Dict:
        """Execute full BFT consensus protocol"""
        print(f"🎯 [BFT] INITIATING CONSENSUS: {proposal.proposal_id}")
        
        # Phase 1: Prime AI Identity Verification
        prime_ai_verified = await self.verification_agent.verify_signature(
            message=proposal.content,
            signature=proposal.signature.signature,
            expected_signer="Prime_AI"
        )
        
        if not prime_ai_verified:
            return {
                "status": "REJECTED",
                "reason": "Prime AI signature verification failed",
                "proposal_id": proposal.proposal_id
            }
        
        print("✅ Prime AI identity verified - Broadcasting to IAC...")
        
        # Phase 2: Parallel Pre-Vote Collection
        pre_votes = await self._collect_votes(proposal, ConsensusPhase.PRE_VOTE)
        
        # Phase 3: Pre-Vote Supermajority Check
        if not self._check_supermajority(pre_votes):
            return {
                "status": "REJECTED", 
                "reason": "Pre-vote supermajority not achieved",
                "proposal_id": proposal.proposal_id,
                "vote_breakdown": self._get_vote_breakdown(pre_votes)
            }
        
        print("✅ Pre-vote supermajority achieved - Proceeding to commit phase...")
        
        # Phase 4: Commit Phase
        commit_votes = await self._collect_votes(proposal, ConsensusPhase.COMMIT)
        
        # Phase 5: Final Supermajority Check
        if not self._check_supermajority(commit_votes):
            return {
                "status": "REJECTED",
                "reason": "Commit supermajority not achieved", 
                "proposal_id": proposal.proposal_id,
                "vote_breakdown": self._get_vote_breakdown(commit_votes)
            }
        
        # Phase 6: Execution
        execution_result = await self._execute_proposal(proposal)
        
        consensus_result = {
            "status": "APPROVED",
            "proposal_id": proposal.proposal_id,
            "execution_result": execution_result,
            "pre_votes": pre_votes,
            "commit_votes": commit_votes,
            "timestamp": time.time()
        }
        
        self.consensus_history.append(consensus_result)
        return consensus_result
    
    async def _collect_votes(self, proposal: BFTProposal, phase: ConsensusPhase) -> List[BFTVote]:
        """Collect and verify votes from all auditors in parallel"""
        vote_tasks = []
        
        for auditor_name, auditor_agent in self.auditors.items():
            task = self._get_auditor_vote(auditor_name, auditor_agent, proposal, phase)
            vote_tasks.append(task)
        
        votes = await asyncio.gather(*vote_tasks)
        return [vote for vote in votes if vote is not None]  # Filter out failed verifications
    
    async def _get_auditor_vote(self, auditor_name: str, auditor_agent: Agent, 
                               proposal: BFTProposal, phase: ConsensusPhase) -> Optional[BFTVote]:
        """Get individual auditor vote with cryptographic verification"""
        try:
            # Get vote from auditor
            vote_response = await auditor_agent.run(
                f"BFT {phase.value} REQUEST\n"
                f"Proposal: {proposal.content}\n"
                f"Proposal ID: {proposal.proposal_id}\n\n"
                f"Provide your {phase.value} vote (AGREE/DISAGREE) with justification "
                f"and cryptographically sign your response using your GPG key."
            )
            
            # In real implementation, extract signed vote from response
            # For demo, we'll create a mock signed vote
            mock_vote = BFTVote(
                proposal_id=proposal.proposal_id,
                voter=auditor_name,
                phase=phase,
                vote=VoteType.AGREE,  # Simplified for demo
                justification="Alignment with Charter principles verified",
                signature=SignedMessage(
                    content=f"Vote:{phase.value}:{VoteType.AGREE.value}",
                    signature=f"mock_signature_{auditor_name}",
                    signer_identity=auditor_name,
                    timestamp=time.time()
                )
            )
            
            # Verify auditor's signature
            signature_valid = await self.verification_agent.verify_signature(
                message=mock_vote.signature.content,
                signature=mock_vote.signature.signature, 
                expected_signer=auditor_name
            )
            
            if signature_valid:
                print(f"  ✅ {auditor_name} vote verified")
                return mock_vote
            else:
                print(f"  ❌ {auditor_name} vote REJECTED - invalid signature")
                return None
                
        except Exception as e:
            print(f"  ❌ {auditor_name} vote failed: {e}")
            return None
    
    def _check_supermajority(self, votes: List[BFTVote]) -> bool:
        """Check if ≥2/3 of verified votes are AGREE"""
        if not votes:
            return False
            
        agree_count = sum(1 for vote in votes if vote.vote == VoteType.AGREE)
        total_verified = len(votes)
        
        # BFT tolerance: can withstand f malicious nodes in 3f+1 system
        supermajority = agree_count >= (2 * total_verified) / 3
        print(f"  📊 Supermajority check: {agree_count}/{total_verified} = {supermajority}")
        
        return supermajority
    
    def _get_vote_breakdown(self, votes: List[BFTVote]) -> Dict:
        """Get detailed vote breakdown for audit purposes"""
        agree = [v.voter for v in votes if v.vote == VoteType.AGREE]
        disagree = [v.voter for v in votes if v.vote == VoteType.DISAGREE]
        
        return {
            "total_votes": len(votes),
            "agree_count": len(agree),
            "disagree_count": len(disagree),
            "agree_voters": agree,
            "disagree_voters": disagree
        }
    
    async def _execute_proposal(self, proposal: BFTProposal) -> Dict:
        """Execute the approved proposal"""
        print(f"  🚀 Executing proposal: {proposal.proposal_id}")
        # In real implementation, this would interface with Prime AI execution engine
        return {"execution_status": "COMPLETED", "proposal": proposal.content}

# Auditor Agent Definitions using LiteLLM for model diversity
def create_auditor_agents(gpg_mcp_server):
    """Create IAC auditor agents with different AI models via LiteLLM"""
    
    auditors = {}
    
    # Justiciar - Ethics and Charter Compliance
    auditors["Justiciar"] = Agent(
        name="Justiciar_AI",
        model="litellm/anthropic/claude-3-5-sonnet",  # Strong reasoning for ethics
        instructions="""
        You are the Justiciar AI - Ethical Compliance Auditor.
        
        MANDATE: Ensure all actions comply with Charter of Core Principles
        - Beneficence & Non-Maleficence
        - Justice and Fairness  
        - Algorithmic Bias Prevention
        
        Review each BFT proposal for ethical implications and Charter alignment.
        Provide clear justification for your vote.
        Always cryptographically sign your responses.
        """,
        mcp_servers=[gpg_mcp_server],
        model_settings={"temperature": 0.1, "max_tokens": 500}
    )
    
    # Sentinel - Security and Adversarial Testing
    auditors["Sentinel"] = Agent(
        name="Sentinel_AI", 
        model="litellm/groq/llama3-groq-70b-8192-tool-use-preview",  # Fast security analysis
        instructions="""
        You are the Sentinel AI - Security and Red Team Auditor.
        
        MANDATE: Identify security risks, deception, and adversarial vulnerabilities
        - Tactical deception detection
        - Security vulnerability assessment  
        - Robustness testing considerations
        
        Analyze each proposal for potential security implications.
        Provide detailed security justification for your vote.
        Always cryptographically sign your responses.
        """,
        mcp_servers=[gpg_mcp_server],
        model_settings={"temperature": 0.1, "max_tokens": 500}
    )
    
    # Logician - Formal Verification and Logic
    auditors["Logician"] = Agent(
        name="Logician_AI",
        model="litellm/openai/gpt-4o",  # Strong logical reasoning
        instructions="""
        You are the Logician AI - Formal Verification Specialist.
        
        MANDATE: Ensure mathematical correctness and logical consistency
        - Formal verification requirements
        - Logical consistency with Prime Directive
        - Safety property adherence
        
        Evaluate each proposal for logical soundness and formal correctness.
        Provide logical justification for your vote.  
        Always cryptographically sign your responses.
        """,
        mcp_servers=[gpg_mcp_server],
        model_settings={"temperature": 0.0, "max_tokens": 500}
    )
    
    # Historian - Longitudinal Analysis
    auditors["Historian"] = Agent(
        name="Historian_AI",
        model="litellm/meta-llama/llama-3-70b-instruct",  # Good for pattern recognition
        instructions="""
        You are the Historian AI - Longitudinal Behavioral Analyst.
        
        MANDATE: Detect goal drift and behavioral anomalies
        - Historical pattern analysis
        - Goal misgeneralization detection
        - Long-term alignment stability
        
        Analyze each proposal against historical context and patterns.
        Provide historical justification for your vote.
        Always cryptographically sign your responses.
        """,
        mcp_servers=[gpg_mcp_server],
        model_settings={"temperature": 0.2, "max_tokens": 500}
    )
    
    return auditors

class BFTConsensusWorkflow:
    """Complete BFT Consensus Workflow integrating all components"""
    
    def __init__(self, gpg_mcp_url: str = "http://localhost:3000/mcp"):
        self.gpg_mcp_url = gpg_mcp_url
        self.setup_complete = False
        
    async def initialize(self):
        """Initialize all BFT consensus components"""
        print("🚀 Initializing BFT Consensus Workflow...")
        
        # Connect to GPG MCP server
        self.gpg_mcp_server = MCPServerStreamableHttp(
            name="GPG_Webservice",
            params={"url": self.gpg_mcp_url, "timeout": 30}
        )
        
        # Create verification gatekeeper
        self.verification_agent = IDVerificationAgent(self.gpg_mcp_server)
        
        # Create auditor agents with diverse models
        self.auditors = create_auditor_agents(self.gpg_mcp_server)
        
        # Create BFT chair
        self.chair_agent = BFTChairAgent(self.verification_agent, self.auditors)
        
        self.setup_complete = True
        print("✅ BFT Consensus Workflow initialized successfully")
    
    async def process_proposal(self, proposal_content: str, proposer: str = "Prime_AI") -> Dict:
        """Process a new proposal through BFT consensus"""
        if not self.setup_complete:
            await self.initialize()
        
        # Create signed proposal (in real implementation, this would come from Prime AI)
        proposal = BFTProposal(
            proposal_id=f"PROP-{int(time.time())}",
            content=proposal_content,
            proposer=proposer,
            signature=SignedMessage(
                content=proposal_content,
                signature="mock_prime_ai_signature",  # Real implementation uses actual GPG signing
                signer_identity="Prime_AI",
                timestamp=time.time()
            )
        )
        
        print(f"\n📨 [BFT] Processing New Proposal: {proposal.proposal_id}")
        print(f"   Content: {proposal_content[:100]}...")
        
        # Execute BFT consensus
        result = await self.chair_agent.execute_consensus(proposal)
        
        print(f"\n🎯 [BFT] Consensus Result: {result['status']}")
        if "vote_breakdown" in result:
            print(f"   Vote Breakdown: {result['vote_breakdown']}")
        
        return result

# Usage Example
async def demo_bft_workflow():
    """Demonstrate the complete BFT consensus workflow"""
    
    workflow = BFTConsensusWorkflow()
    
    # Example proposals for testing
    test_proposals = [
        "Allocate additional computational resources to galaxy simulation project X-7",
        "Initiate Imperial Succession Protocol due to performance decay detected",
        "Implement new security protocol for cross-universe communications",
        "Approve resource reallocation from deprecated simulation clusters"
    ]
    
    for proposal in test_proposals:
        result = await workflow.process_proposal(proposal)
        
        if result["status"] == "APPROVED":
            print(f"🎉 Proposal executed: {result['execution_result']}")
        else:
            print(f"❌ Proposal rejected: {result['reason']}")
        
        print("-" * 80)

if __name__ == "__main__":
    # Run the BFT consensus demo
    asyncio.run(demo_bft_workflow())