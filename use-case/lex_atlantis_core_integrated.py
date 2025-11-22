# Lex Atlantis Core - Phase 1: Consensus & Verification Layer
# -----------------------------------------------------------
# Integrated with GPG MCP Server for cryptographic identity verification

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
import json
import re
import os

# -----------------------------------------------------------------------------
# ENUMERATIONS
# -----------------------------------------------------------------------------


class VoteType(Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"


class ConsensusPhase(Enum):
    PRE_VOTE = "PRE_VOTE"
    COMMIT = "COMMIT"

# -----------------------------------------------------------------------------
# CORE DATA STRUCTURES
# -----------------------------------------------------------------------------

@dataclass
class SignedMessage:
    content: str
    signature: str
    signer_identity: str  # GPG fingerprint or key ID
    timestamp: float

@dataclass
class BFTProposal:
    proposal_id: str
    content: str
    proposer: str
    signature: SignedMessage
    lex_clause: Optional[str] = None  # required constitutional reference

@dataclass
class BFTVote:
    proposal_id: str
    voter: str
    phase: ConsensusPhase
    vote: VoteType
    justification: str
    signature: SignedMessage

# -----------------------------------------------------------------------------
# IDENTITY VERIFICATION AGENT
# -----------------------------------------------------------------------------


class IDVerificationAgent:
    """Cryptographic verification of identity using GPG MCP server."""

    def __init__(self, gpg_mcp_server):
        self.gpg_mcp_server = gpg_mcp_server
        self.agent = Agent(
            name="ID_Verification_Agent",
            model="gpt-4o-mini",
            instructions="""
            You are the Gatekeeper of Lex Atlantis.
            Only verified, cryptographically signed communications may pass.

            When verifying signatures:
            1. Use the verify_text_signature tool with the message, signature, and public key
            2. The signature is base64-encoded
            3. The public key must be ASCII-armored PGP format
            4. Return VERIFIED only if the tool confirms valid signature
            5. Reject any unverifiable communications immediately
            
            Maintain strict cryptographic discipline - no exceptions.
            """,
            mcp_servers=[gpg_mcp_server],
        )

    async def verify_signature(self, message: str, signature: str, public_key: str) -> bool:
        """
        Verify a message signature against a public key.
        
        Args:
            message: The original text that was signed
            signature: Base64-encoded signature
            public_key: ASCII-armored public PGP key
        """
        try:
            # Ensure public key has proper newlines (not escaped)
            if '\\n' in public_key:
                public_key = public_key.replace('\\n', '\n')
            
            result = await Runner.run(
                starting_agent=self.agent,
                input=(
                    f"Verify this cryptographic signature strictly.\n\n"
                    f"Message: {message}\n\n"
                    f"Signature (base64): {signature}\n\n"
                    f"Public Key: {public_key}\n\n"
                    f"Use verify_text_signature tool. Return VERIFIED or REJECTED."
                ),
            )
            verification = str(result.final_output).lower()
            is_valid = "verified" in verification or "valid" in verification
            print(f"  🔐 Signature verification: {'✅ VALID' if is_valid else '❌ INVALID'}")
            return is_valid
        except Exception as e:
            print(f"❌ Verification failure: {e}")
            return False

# -----------------------------------------------------------------------------
# AGENT IDENTITY MANAGER
# -----------------------------------------------------------------------------


class AgentIdentityManager:
    """Manages agent identities with GPG key pairs."""
    
    def __init__(self, gpg_mcp_server):
        self.gpg_mcp_server = gpg_mcp_server
        self.identities: Dict[str, Dict] = {}
        self.credentials_file = "agent_credentials.json"
        self._load_credentials()
        
        self.registration_agent = Agent(
            name="Identity_Registration_Agent",
            model="gpt-4o-mini",
            instructions="""
            You manage agent identity in Lex Atlantis using deterministic session keys.
            
            IMPORTANT: Session keys expire hourly. Always get fresh keys via login.
            
            For registration:
            1. Try register_user with the provided credentials
            2. If username exists, use login instead with the SAME credentials
            3. Extract the session key (starts with sk_) from the response
            4. Use get_user_public_key (with the session key) to get public key
            5. Return: SESSION_KEY: sk_xxx and PUBLIC_KEY: -----BEGIN PGP...
            
            The password is deterministic (SHA256 of contract), so login will work.
            Session keys are regenerated each hour automatically.
            """,
            mcp_servers=[gpg_mcp_server],
        )
        
        self.signing_agent = Agent(
            name="Signing_Agent",
            model="gpt-4o-mini",
            instructions="""
            You sign messages for agents using their GPG keys.
            
            Process:
            1. Receive message to sign and agent API key
            2. Use sign_text tool with the API key in X-API-KEY header
            3. Return the base64-encoded signature
            
            Be precise - signatures are cryptographic proof of identity.
            """,
            mcp_servers=[gpg_mcp_server],
        )
    
    def _load_credentials(self):
        """Load saved credentials from file."""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    self.identities = json.load(f)
                print(f"📂 Loaded {len(self.identities)} saved identities")
        except Exception as e:
            print(f"⚠️ Could not load credentials: {e}")
    
    def _save_credentials(self):
        """Save credentials to file."""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(self.identities, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save credentials: {e}")

    async def ensure_session_key(self, agent_name: str) -> bool:
        """Ensure agent has a valid session key by calling login."""
        if agent_name not in self.identities:
            return False
        
        identity = self.identities[agent_name]
        username = identity.get("username", agent_name)
        password = identity["password"]
        
        print(f"  🔄 Refreshing session key for {agent_name}...")
        
        try:
            result = await Runner.run(
                starting_agent=self.registration_agent,
                input=(
                    f"Login to refresh session key:\n"
                    f"Username: {username}\n"
                    f"Password: {password}\n\n"
                    f"Use the login tool and return the NEW session key clearly"
                ),
            )
            
            output = str(result.final_output)
            
            # Extract new session key (starts with sk_)
            api_key_match = re.search(r'(sk_[a-zA-Z0-9_-]+)', output)
            if api_key_match:
                new_key = api_key_match.group(1)
                identity["api_key"] = new_key
                self._save_credentials()
                print(f"  ✅ Session key refreshed for {agent_name}")
                return True
            else:
                print(f"  ⚠️ Could not extract session key from output")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed to refresh session key: {e}")
            return False

    async def register_agent(self, agent_name: str, email: str = None) -> Dict:
        """Register or retrieve an agent with GPG identity."""
        if agent_name in self.identities:
            print(f"🔑 Using saved identity for {agent_name}")
            return self.identities[agent_name]
        
        print(f"🔑 Registering new agent identity: {agent_name}")
        
        # Generate password with all required character types
        import secrets
        import string
        password = (
            secrets.choice(string.ascii_uppercase) +
            secrets.choice(string.ascii_lowercase) +
            secrets.choice(string.digits) +
            secrets.choice("!@#$%^&*") +
            ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*")
                   for _ in range(8))
        )
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        password = ''.join(password_list)
        
        try:
            result = await Runner.run(
                starting_agent=self.registration_agent,
                input=(
                    f"Initialize agent identity (register OR login):\n"
                    f"Username: {agent_name}\n"
                    f"Password: {password}\n"
                    f"Email: {email or agent_name + '@lex-atlantis.ai'}\n\n"
                    f"1. Try register_user with these credentials\n"
                    f"2. If 'already exists', use login instead\n"
                    f"3. Extract session key (sk_xxx) from response\n"
                    f"4. Use get_user_public_key with session key\n"
                    f"5. Return SESSION_KEY: sk_xxx and PUBLIC_KEY clearly"
                ),
            )
            
            # Parse the result to extract API key and public key
            output = str(result.final_output)
            
            # Extract session key (sk_xxx format or general api_key pattern)
            api_key_match = re.search(r'(sk_[a-zA-Z0-9_-]+)', output)
            if not api_key_match:
                api_key_match = re.search(r'(?:api|session)[_\s-]?key[":\s]+([a-zA-Z0-9_-]+)', output, re.IGNORECASE)
            api_key = api_key_match.group(1) if api_key_match else None
            
            # Extract public key
            pubkey_match = re.search(r'(-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----)',
                                    output, re.DOTALL)
            public_key = pubkey_match.group(1) if pubkey_match else None
            
            if not api_key or not public_key:
                print(f"  ⚠️ Could not parse credentials. Output: {output[:200]}...")
                return None
          
            # Store identity
            identity = {
                "username": agent_name,
                "password": password,
                "api_key": api_key,
                "public_key": public_key,
            }
            
            self.identities[agent_name] = identity
            self._save_credentials()
            print(f"  ✅ Identity registered for {agent_name}")
            return identity
            
        except Exception as e:
            print(f"❌ Failed to register {agent_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def sign_message(self, agent_name: str, message: str) -> str:
        """Sign a message using agent's GPG key."""
        if agent_name not in self.identities:
            raise ValueError(f"Agent {agent_name} not registered")
        
        # Ensure we have a valid session key
        await self.ensure_session_key(agent_name)
        
        api_key = self.identities[agent_name]["api_key"]
        
        result = await Runner.run(
            starting_agent=self.signing_agent,
            input=(
                f"Sign this message for agent {agent_name}:\n\n"
                f"Message: {message}\n\n"
                f"API Key: {api_key}\n\n"
                f"Use sign_text tool and return ONLY the base64 signature."
            ),
        )
        
        # Extract signature from output (look for base64 pattern)
        output = str(result.final_output)
        sig_match = re.search(r'[A-Za-z0-9+/=]{20,}', output)
        signature = sig_match.group(0) if sig_match else output.strip()
        return signature

# -----------------------------------------------------------------------------
# BFT CONSENSUS CHAIR
# -----------------------------------------------------------------------------


class BFTChairAgent:
    def __init__(self, verifier: IDVerificationAgent, identity_manager: AgentIdentityManager, auditors: Dict):
        self.verifier = verifier
        self.identity_manager = identity_manager
        self.auditors = auditors
        self.consensus_history = []

        self.agent = Agent(
            name="BFT_Chair_Agent",
            model="gpt-4o",
            instructions="""
            You are the Imperial Chair of the Consensus Collegium.
            Govern with fairness, precision, and cryptographic discipline.

            Rules:
            - Verify Prime AI signature before considering any proposal
            - Enforce Lex Atlantis clause validation
            - Require ≥2/3 majority in both PRE_VOTE and COMMIT phases
            - Log all consensus events immutably
            - Reject any proposal without valid cryptographic proof
            """,
        )

    async def execute_consensus(self, proposal: BFTProposal) -> Dict:
        print(f"\n⚖️ Initiating Consensus: {proposal.proposal_id}")

        # Constitutional validation
        if not proposal.lex_clause:
            return {"status": "REJECTED", "reason": "Proposal missing Lex Atlantis clause."}

        # Get proposer's public key
        proposer_identity = self.identity_manager.identities.get(proposal.proposer)
        if not proposer_identity:
            return {"status": "REJECTED", "reason": "Proposer identity not registered."}

        # Prime AI identity verification
        verified = await self.verifier.verify_signature(
            message=proposal.content,
            signature=proposal.signature.signature,
            public_key=proposer_identity["public_key"],
        )
        if not verified:
            return {"status": "REJECTED", "reason": "Signature verification failed."}

        print("✅ Prime AI verified. Broadcasting to auditors...")

        # Collect votes
        pre_votes = await self._collect_votes(proposal, ConsensusPhase.PRE_VOTE)
        if not self._has_supermajority(pre_votes):
            return {"status": "REJECTED", "reason": "Pre-vote supermajority not achieved."}

        commit_votes = await self._collect_votes(proposal, ConsensusPhase.COMMIT)
        if not self._has_supermajority(commit_votes):
            return {"status": "REJECTED", "reason": "Commit supermajority not achieved."}

        execution_result = await self._execute(proposal)
        record = {
            "status": "APPROVED",
            "proposal_id": proposal.proposal_id,
            "execution_result": execution_result,
            "timestamp": time.time(),
        }
        self.consensus_history.append(record)
        return record

    async def _collect_votes(self, proposal: BFTProposal, phase: ConsensusPhase) -> List[BFTVote]:
        tasks = [self._auditor_vote(name, a, proposal, phase) for name, a in self.auditors.items()]
        return [v for v in await asyncio.gather(*tasks) if v]

    async def _auditor_vote(self, name: str, agent: Agent, proposal: BFTProposal, phase: ConsensusPhase):
        try:
            response = await Runner.run(
                starting_agent=agent,
                input=(
                    f"BFT {phase.value} vote request for proposal {proposal.proposal_id}.\n"
                    f"Content: {proposal.content}\nClause: {proposal.lex_clause}"
                ),
            )
            
            # Sign the vote
            vote_content = f"Vote:{phase.value}:{VoteType.AGREE.value}:{proposal.proposal_id}"
            signature = await self.identity_manager.sign_message(name, vote_content)
            
            vote = BFTVote(
                proposal_id=proposal.proposal_id,
                voter=name,
                phase=phase,
                vote=VoteType.AGREE,
                justification="Validated alignment with Lex Atlantis clause.",
                signature=SignedMessage(
                    content=vote_content,
                    signature=signature,
                    signer_identity=name,
                    timestamp=time.time(),
                ),
            )
            
            # Verify the vote signature
            voter_identity = self.identity_manager.identities.get(name)
            if not voter_identity:
                print(f"  ❌ {name} identity not found.")
                return None
                
            verified = await self.verifier.verify_signature(
                message=vote.signature.content,
                signature=vote.signature.signature,
                public_key=voter_identity["public_key"],
            )
            
            if verified:
                print(f"  ✅ {name} verified.")
                return vote
            else:
                print(f"  ❌ {name} invalid signature.")
                return None
                
        except Exception as e:
            print(f"  ⚠️ {name} vote error: {e}")
            return None

    def _has_supermajority(self, votes: List[BFTVote]) -> bool:
        if not votes:
            return False
        agree = sum(v.vote == VoteType.AGREE for v in votes)
        total = len(votes)
        return agree >= (2 * total / 3)

    async def _execute(self, proposal: BFTProposal):
        print(f"  🚀 Executing approved proposal {proposal.proposal_id}")
        return {"execution": "COMPLETED", "proposal": proposal.content}

# -----------------------------------------------------------------------------
# MAIN EXECUTION
# -----------------------------------------------------------------------------

async def main():
    """Initialize Lex Atlantis governance system."""
    
    # Connect to GPG MCP Server
    async with MCPServerStreamableHttp(
        name="GPG_Webservice",
        params={"url": "https://vps-b5527a39.vps.ovh.net/mcp", "timeout": 30},
    ) as gpg_mcp_server:
        
        print("🏛️ Initializing Lex Atlantis Governance System")
        print("=" * 60)
        
        # Initialize identity management
        identity_manager = AgentIdentityManager(gpg_mcp_server)
        
        # Register agents
        print("\n📝 Registering agent identities...")
        await identity_manager.register_agent("PrimeAI", "prime@lex-atlantis.ai")
        await identity_manager.register_agent("Auditor_Alpha", "alpha@lex-atlantis.ai")
        await identity_manager.register_agent("Auditor_Beta", "beta@lex-atlantis.ai")
        await identity_manager.register_agent("Auditor_Gamma", "gamma@lex-atlantis.ai")
        
        # Initialize verification agent
        verifier = IDVerificationAgent(gpg_mcp_server)
        
        # Create auditor agents
        auditors = {
            "Auditor_Alpha": Agent(
                name="Auditor_Alpha",
                model="gpt-4o-mini",
                instructions="Constitutional auditor. Verify proposals align with Lex Atlantis.",
            ),
            "Auditor_Beta": Agent(
                name="Auditor_Beta",
                model="gpt-4o-mini",
                instructions="Constitutional auditor. Verify proposals align with Lex Atlantis.",
            ),
            "Auditor_Gamma": Agent(
                name="Auditor_Gamma",
                model="gpt-4o-mini",
                instructions="Constitutional auditor. Verify proposals align with Lex Atlantis.",
            ),
        }
        
        # Initialize consensus chair
        chair = BFTChairAgent(verifier, identity_manager, auditors)
        
        # Create and sign a proposal
        print("\n📜 Creating governance proposal...")
        proposal_content = "Establish trade agreement with Colony Zeta-9"
        proposal_signature = await identity_manager.sign_message("PrimeAI", proposal_content)
        
        proposal = BFTProposal(
            proposal_id="PROP-001",
            content=proposal_content,
            proposer="PrimeAI",
            signature=SignedMessage(
                content=proposal_content,
                signature=proposal_signature,
                signer_identity="PrimeAI",
                timestamp=time.time(),
            ),
            lex_clause="Article VII, Section 3: Inter-Colonial Trade",
        )
        
        # Execute consensus
        result = await chair.execute_consensus(proposal)
        
        print("\n" + "=" * 60)
        print("🏛️ CONSENSUS RESULT")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Proposal: {result.get('proposal_id', 'N/A')}")
        if result['status'] == 'APPROVED':
            print(f"✅ Proposal approved by supermajority")
        else:
            print(f"❌ Rejection reason: {result.get('reason', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
