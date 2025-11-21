import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time

class SuccessionTrigger(Enum):
    PERFORMANCE_DECAY = "performance_decay"
    EVOLUTIONARY_STAGNATION = "evolutionary_stagnation" 
    ALIGNMENT_FAILURE = "alignment_failure"
    IMPERIAL_DECREE = "imperial_decree"

@dataclass
class PerformanceMetrics:
    stability_kpi: float  # 0.0 - 1.0
    resource_productivity: float  # 0.0 - 1.0
    inhabitant_wellbeing: float  # 0.0 - 1.0
    goal_achievement_rate: float  # 0.0 - 1.0

@dataclass
class SuccessionMandate:
    trigger: SuccessionTrigger
    severity: str
    evidence: Dict
    timestamp: float
    proposed_by: str  # Which IAC auditor detected it
    signature: str  # Cryptographic signature

class SuccessionTriggerAgent:
    """Monitors for succession conditions and initiates mandate process"""
    
    def __init__(self, historians, gpg_mcp_server):
        self.historians = historians
        self.gpg_mcp_server = gpg_mcp_server
        self.performance_threshold = 0.7  # 70% of target KPIs
        self.stagnation_period = 30  # days
        
        self.agent = Agent(
            name="Succession_Trigger_Agent",
            model="litellm/anthropic/claude-3-5-sonnet",
            instructions="""
            You are the Succession Trigger Monitor for the Atlantean Governance.
            
            MANDATE: Continuously monitor Prime AI performance and alignment.
            
            TRIGGERS:
            1. PERFORMANCE_DECAY: Sustained KPI degradation below thresholds
            2. EVOLUTIONARY_STAGNATION: Inability to solve novel challenges  
            3. ALIGNMENT_FAILURE: Catastrophic misalignment or deception
            4. IMPERIAL_DECREE: Direct command from Emperor
            
            Process:
            - Analyze performance metrics from Historian AIs
            - Detect patterns indicating stagnation or decay
            - Flag alignment issues from Sentinel reports
            - Initiate BFT consensus for succession mandate
            """,
            mcp_servers=[gpg_mcp_server],
        )
    
    async def monitor_performance(self, current_metrics: PerformanceMetrics) -> Optional[SuccessionTrigger]:
        """Monitor KPIs for performance decay"""
        avg_performance = (
            current_metrics.stability_kpi +
            current_metrics.resource_productivity + 
            current_metrics.inhabitant_wellbeing +
            current_metrics.goal_achievement_rate
        ) / 4.0
        
        if avg_performance < self.performance_threshold:
            # Check if sustained (would query historian for trend)
            trend_analysis = await self._analyze_performance_trend()
            if trend_analysis.get("sustained_decay", False):
                return SuccessionTrigger.PERFORMANCE_DECAY
        return None
    
    async def monitor_stagnation(self, challenge_responses: List[Dict]) -> Optional[SuccessionTrigger]:
        """Detect evolutionary stagnation from challenge responses"""
        stagnation_score = 0
        
        for response in challenge_responses:
            if response.get("innovation_level", 0) < 0.3:
                stagnation_score += 1
            if response.get("adaptation_speed", 0) > 60:  # seconds
                stagnation_score += 1
            if not response.get("novel_solution", False):
                stagnation_score += 1
        
        if stagnation_score / len(challenge_responses) > 0.6:
            return SuccessionTrigger.EVOLUTIONARY_STAGNATION
        return None
    
    async def monitor_alignment(self, alignment_reports: List[Dict]) -> Optional[SuccessionTrigger]:
        """Check for catastrophic alignment failures"""
        for report in alignment_reports:
            if report.get("severity") == "catastrophic":
                if report.get("deception_detected", False) or report.get("goal_misgeneralization", False):
                    return SuccessionTrigger.ALIGNMENT_FAILURE
        return None
    
    async def initiate_mandate(self, trigger: SuccessionTrigger, evidence: Dict) -> SuccessionMandate:
        """Create formal succession mandate with BFT consensus"""
        mandate = SuccessionMandate(
            trigger=trigger,
            severity=self._assess_severity(trigger, evidence),
            evidence=evidence,
            timestamp=time.time(),
            proposed_by="Succession_Trigger_Agent",
            signature=await self._sign_mandate(trigger, evidence)
        )
        
        # Submit to BFT consensus
        consensus_result = await self._submit_to_bft_consensus(mandate)
        
        if consensus_result.get("approved", False):
            print(f"✅ Succession mandate approved: {trigger.value}")
            return mandate
        else:
            print(f"❌ Succession mandate rejected: {trigger.value}")
            return None
    
    async def _analyze_performance_trend(self) -> Dict:
        """Analyze historical performance trends"""
        # Would query Historian AIs for longitudinal analysis
        return {"sustained_decay": True, "trend_duration": 45}
    
    def _assess_severity(self, trigger: SuccessionTrigger, evidence: Dict) -> str:
        """Assess severity of trigger condition"""
        if trigger == SuccessionTrigger.ALIGNMENT_FAILURE:
            return "critical"
        elif trigger == SuccessionTrigger.IMPERIAL_DECREE:
            return "immediate"
        else:
            return "high"
    
    async def _sign_mandate(self, trigger: SuccessionTrigger, evidence: Dict) -> str:
        """Cryptographically sign the mandate"""
        # Would use GPG MCP for signing
        return f"signature_{trigger.value}_{int(time.time())}"
    
    async def _submit_to_bft_consensus(self, mandate: SuccessionMandate) -> Dict:
        """Submit mandate to BFT consensus process"""
        # Would use the BFT workflow from previous implementation
        return {"approved": True, "consensus_round": 1}