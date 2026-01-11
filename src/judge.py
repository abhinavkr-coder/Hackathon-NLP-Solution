"""
judge.py - Consistency Judgment Engine

This is where we make the final decision: is the backstory consistent with the novel?

The challenge here is subtle. We're not checking for word-for-word matches or
simple contradictions. We're asking a deeper question: given the constraints
established throughout the narrative, could this backstory plausibly lead to
the events we observe?

Updated to include strict anti-hallucination checks that verify specific details
(names, dates, entities) actually appear in the evidence before accepting backstory claims.
"""
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("CEREBRAS_API_KEY")
if not API_KEY:
    raise RuntimeError("CEREBRAS_API_KEY not found in .env")

import logging
import os
import re
import time
from typing import List, Dict, Tuple
from openai import OpenAI

# Import semantic analyzer for enhanced analysis
from semantic_analyzer import enhance_evidence_with_semantic_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsistencyJudge:
    """
    Makes consistency judgments using evidence-based reasoning with anti-hallucination detection.
    
    We use a multi-stage approach:
    1. Analyze retrieved evidence for support and contradiction
    2. Verify specific details (entities, dates) actually appear in evidence
    3. Weight evidence by quality and relevance
    4. Apply consistency heuristics with hallucination penalty
    5. Make final judgment with confidence score
    
    This can be done with or without an LLM, depending on resources.
    """
    
    def __init__(self, use_llm: bool = True, api_key: str = None):
        """
        Initialize the judge.
        
        Args:
            use_llm: Whether to use an LLM for sophisticated reasoning.
                    If False, uses rule-based heuristics (faster but less accurate)
            api_key: API key for LLM (if use_llm=True). If None, will be read from env
        """
        self.use_llm = use_llm
        self.api_key = api_key
        
        if use_llm and not api_key:
            self.api_key = os.getenv('CEREBRAS_API_KEY')
            if not self.api_key:
                logger.warning(
                    "No API key provided and CEREBRAS_API_KEY not in environment. "
                    "Falling back to rule-based judgment."
                )
                self.use_llm = False
    
    def judge_consistency(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        Main entry point for consistency judgment with semantic enhancement and hallucination detection.
        
        Returns:
            prediction: 1 (consistent) or 0 (inconsistent)
            rationale: Explanation of the decision
            confidence: Score between 0 and 1 indicating decision confidence
        """
        # Enhance evidence with semantic analysis
        try:
            enhanced_evidence, semantic_info = enhance_evidence_with_semantic_analysis(
                evidence, backstory
            )
            
            # CRITICAL HALLUCINATION CHECK:
            # If the backstory contains specific details (dates/entities) but they are 
            # almost entirely missing from the evidence, this is a strong signal of fabrication.
            detail_stats = semantic_info.get('detail_check', {})
            overlap_score = detail_stats.get('overlap_score', 1.0)
            total_details = detail_stats.get('total_details', 0)
            missing_details = detail_stats.get('missing_details', [])
            
            # If we have many details (>=2) but very low overlap (<20%), it's likely a hallucination
            is_likely_hallucination = (total_details >= 2 and overlap_score < 0.20)
            
            # Use semantic analysis to inform judgment
            if self.use_llm:
                prediction, rationale, confidence = self._judge_with_llm_enhanced(
                    backstory, enhanced_evidence, novel_id, semantic_info
                )
            else:
                prediction, rationale, confidence = self._judge_with_heuristics_enhanced(
                    backstory, enhanced_evidence, novel_id, semantic_info
                )
            
            # HALLUCINATION OVERRIDE:
            # If hallucination is detected and the model predicted consistent,
            # override to inconsistent with high confidence
            if is_likely_hallucination and prediction == 1:
                logger.info(
                    f"Hallucination detected for {novel_id}. "
                    f"Missing details: {missing_details[:3]}"
                )
                prediction = 0
                rationale = (
                    f"Inconsistent: The backstory relies on specific details "
                    f"({', '.join(str(d) for d in missing_details[:3])}...) "
                    "that are completely absent from the narrative evidence."
                )
                confidence = 0.90
                
            # Apply confidence boost if evidence exists and no hallucination detected
            elif len(enhanced_evidence) > 0 and not is_likely_hallucination:
                avg_similarity = sum(e.get('similarity', 0) for e in enhanced_evidence) / len(enhanced_evidence)
                if avg_similarity > 0.40:  # If there's meaningful evidence
                    confidence = max(confidence, 0.88)  # Enforce minimum 0.88 when evidence exists
            
            return prediction, rationale, confidence
            
        except Exception as e:
            logger.warning(f"Semantic analysis failed, falling back to basic judgment: {e}")
            # Fallback to original methods
            if self.use_llm:
                return self._judge_with_llm(backstory, evidence, novel_id)
            else:
                return self._judge_with_heuristics(backstory, evidence, novel_id)

    def _check_antonyms(self, backstory: str, evidence_text: str) -> bool:
        """
        Check for semantic contradictions using common antonym pairs.
        Returns True if a contradiction is found.
        """
        # Common antonym pairs relevant to backstories
        pairs = [
            ('wealthy', 'poverty'), ('rich', 'poor'), ('wealth', 'poor'),
            ('aristocrat', 'peasant'), ('noble', 'commoner'),
            ('loved', 'hated'), ('always', 'never'),
            ('brave', 'cowardly'), ('strong', 'weak'),
            ('dead', 'alive'), ('died', 'survived')
        ]
        
        b_lower = backstory.lower()
        e_lower = evidence_text.lower()
        
        for w1, w2 in pairs:
            # Check if one word is in backstory and the OPPOSITE is in evidence
            if (w1 in b_lower and w2 in e_lower) or \
               (w2 in b_lower and w1 in e_lower):
                logger.info(f"Heuristic contradiction found: {w1} vs {w2}")
                return True
        return False
    
    def _judge_with_heuristics(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        Rule-based consistency checking with improved contradiction detection.
        
        Key heuristics:
        1. Semantic antonyms (wealthy vs poverty)
        2. Strong negation in high-similarity passages
        3. Low overall similarity suggests backstory is unsupported
        """
        if not evidence:
            return 0, "No evidence found to support backstory", 0.5
        
        # Calculate average similarity
        avg_similarity = sum(chunk['similarity'] for chunk in evidence) / len(evidence)
        combined_evidence_text = " ".join([chunk['text'] for chunk in evidence])
        
        # 1. Check for semantic antonyms (wealthy vs poverty)
        if self._check_antonyms(backstory, combined_evidence_text):
             return 0, "Backstory contradicts evidence (antonyms found)", 0.8

        # 2. Check for negation words in high-similarity chunks
        negation_words = ['not', 'never', 'no', 'none', 'nobody', 'nothing', 'impossible', 'cannot']
        contradiction_count = 0
        
        for chunk in evidence[:5]:  # Focus on top 5 most similar
            if chunk['similarity'] > 0.7:
                text_lower = chunk['text'].lower()
                # Only count negation if the chunk actually shares significant words with backstory
                common_words = set(backstory.lower().split()) & set(text_lower.split())
                if len(common_words) > 2 and any(word in text_lower for word in negation_words):
                    contradiction_count += 1
        
        # Decision logic
        if avg_similarity < 0.45:
            # Very low similarity - backstory might be unrelated to novel
            return 0, "Backstory claims are not supported by the narrative", 0.6
        
        elif contradiction_count >= 1:
            # High-similarity passages with negation
            return 0, "Evidence contains direct negations of backstory claims", 0.7
        
        elif avg_similarity > 0.65 and contradiction_count == 0:
            # High similarity, no clear contradictions
            return 1, "Backstory is well-supported by narrative evidence", 0.8
        
        else:
            # Ambiguous case - Default to consistent if moderately supported
            if avg_similarity > 0.6:
                return 1, "Backstory is plausible given available evidence", 0.55
            else:
                return 0, "Insufficient evidence to confirm backstory", 0.5
    
    def _judge_with_heuristics_enhanced(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str,
        semantic_info: Dict
    ) -> Tuple[int, str, float]:
        """
        Enhanced heuristic judgment incorporating semantic analysis and detail verification.
        
        This combines the basic heuristics with semantic understanding of
        backstory claims, evidence contradictions, causal consistency, and
        strict detail overlap checking to prevent hallucinations.
        """
        # Get base judgment
        base_prediction, base_rationale, base_confidence = self._judge_with_heuristics(
            backstory, evidence, novel_id
        )
        
        # Extract semantic analysis components
        support_score = semantic_info['support_score']
        causal_analysis = semantic_info['causal_analysis']
        contradictions = semantic_info['contradictions']
        detail_check = semantic_info.get('detail_check', {})
        
        # Detail verification scores
        overlap_score = detail_check.get('overlap_score', 1.0)
        total_details = detail_check.get('total_details', 0)
        missing_details = detail_check.get('missing_details', [])
        
        # Start with base confidence
        enhanced_confidence = base_confidence
        
        # Rule 1: Direct Contradictions Override
        if contradictions:
            # Contradictions found - mark as inconsistent with high confidence
            enhanced_confidence = 0.95
            base_prediction = 0
            base_rationale = f"Semantic contradiction detected: {contradictions[0][0][:50]}... vs {contradictions[0][1][:50]}..."
        
        # Rule 2: High Detail Mismatch (Hallucination Detection)
        elif total_details > 0 and overlap_score < 0.25:
            # Specific details mentioned but not found in evidence
            enhanced_confidence = 0.85
            base_prediction = 0
            base_rationale = (
                f"Specific biographical details ({', '.join(str(d) for d in missing_details[:3])}) "
                "in backstory are missing from evidence."
            )
        
        # Rule 3: Strong Support with Detail Verification
        elif base_prediction == 1 and overlap_score > 0.5:
            # High semantic support AND details match
            avg_similarity = sum(e.get('similarity', 0) for e in evidence) / len(evidence) if evidence else 0
            if avg_similarity > 0.65:
                enhanced_confidence = min(0.95, base_confidence + 0.15)
                base_rationale = "Backstory is well-supported by evidence and specific details match."
            else:
                enhanced_confidence = min(0.90, base_confidence + 0.10)
        
        # Rule 4: No contradictions but boost confidence based on support
        elif not contradictions:
            # No contradictions found - boost confidence
            if base_prediction == 1:
                enhanced_confidence = min(0.95, base_confidence + 0.15)
            else:
                enhanced_confidence = min(0.92, base_confidence + 0.12)
        
        # Incorporate semantic support score
        enhanced_confidence = enhanced_confidence * 0.6 + support_score * 0.40
        
        # Causal consistency bonus
        if causal_analysis['causal_consistency'] > 0.75:
            enhanced_confidence = min(0.95, enhanced_confidence + 0.08)
        
        # Enforce minimum confidence for cases with meaningful evidence
        if len(evidence) > 0:
            avg_similarity = sum(e.get('similarity', 0) for e in evidence) / len(evidence)
            if avg_similarity > 0.35 and not (total_details > 0 and overlap_score < 0.25):
                enhanced_confidence = max(enhanced_confidence, 0.88)
        
        return base_prediction, base_rationale, enhanced_confidence
    
    def _judge_with_llm_enhanced(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str,
        semantic_info: Dict
    ) -> Tuple[int, str, float]:
        """
        Enhanced LLM-based judgment with semantic context and anti-hallucination prompting.
        """
        try:
            if not self.api_key:
                logger.warning("No API key available for LLM. Falling back to enhanced heuristics.")
                return self._judge_with_heuristics_enhanced(
                    backstory, evidence, novel_id, semantic_info
                )
            
            # Create enhanced prompt with semantic information and hallucination warnings
            evidence_text = self._format_evidence_for_llm(evidence)
            semantic_context = self._format_semantic_context(semantic_info)
            prompt = self._create_judgment_prompt_with_semantics(
                backstory, evidence_text, semantic_context, semantic_info
            )
            
            # Initialize Cerebras client
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.cerebras.ai/v1"
            )
            response = client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model="llama3.1-8b",
                temperature=0,
                max_tokens=1000,
            )
            
            response_text = response.choices[0].message.content
            prediction, rationale, confidence = self._parse_llm_response(response_text)
            
            logger.info(f"Enhanced LLM judgment for {novel_id}: {prediction} (confidence: {confidence:.2f})")
            return prediction, rationale, confidence
            
        except Exception as e:
            logger.error(f"Error in enhanced LLM judgment: {e}")
            logger.info("Falling back to rule-based enhanced judgment")
            return self._judge_with_heuristics_enhanced(backstory, evidence, novel_id, semantic_info)
        
    def _format_semantic_context(self, semantic_info: Dict) -> str:
        """Format semantic analysis information for the LLM."""
        claims = semantic_info.get('claims', [])
        support_score = semantic_info.get('support_score', 0)
        causal_analysis = semantic_info.get('causal_analysis', {})
        contradictions = semantic_info.get('contradictions', [])
        detail_check = semantic_info.get('detail_check', {})
        
        context_parts = []
        
        context_parts.append(f"SEMANTIC ANALYSIS:")
        context_parts.append(f"- Overall support score: {support_score:.2f}")
        context_parts.append(f"- Causal consistency: {causal_analysis.get('causal_consistency', 0):.2f}")
        context_parts.append(f"- Number of potential contradictions: {len(contradictions)}")
        context_parts.append(f"- Detail overlap score: {detail_check.get('overlap_score', 0):.2f}")
        context_parts.append(f"- Total specific details: {detail_check.get('total_details', 0)}")
        
        if claims:
            context_parts.append(f"\nBACKSTORY CLAIMS:")
            for i, claim in enumerate(claims[:3], 1):  # Top 3 claims
                context_parts.append(f"  {i}. {claim['text']} (Type: {claim['type']}, Importance: {claim['importance']})")
        
        if contradictions:
            context_parts.append(f"\nPOTENTIAL CONTRADICTIONS:")
            for i, (claim, evidence, conf) in enumerate(contradictions[:2], 1):
                context_parts.append(f"  {i}. Claim: {claim[:50]}... vs Evidence: {evidence[:50]}...")
        
        # Add hallucination warning if applicable
        missing_details = detail_check.get('missing_details', [])
        if missing_details:
            context_parts.append(f"\n⚠️ MISSING DETAILS WARNING:")
            context_parts.append(f"The following specific details from the backstory were NOT found in evidence:")
            context_parts.append(f"  {', '.join(str(d) for d in missing_details[:5])}")
            context_parts.append("This strongly suggests the backstory may be fabricated or hallucinated.")
        
        return "\n".join(context_parts)
    
    def _create_judgment_prompt_with_semantics(
        self,
        backstory: str,
        evidence_text: str,
        semantic_context: str,
        semantic_info: Dict
    ) -> str:
        """Create enhanced judgment prompt with semantic analysis and strict anti-hallucination rules."""
        
        prompt = f"""You are an expert narrative consistency analyst. Your task is to determine if a backstory is consistent with evidence from a novel.

BACKSTORY TO EVALUATE:
{backstory}

EVIDENCE FROM NOVEL (ranked by relevance):
{evidence_text}

SEMANTIC ANALYSIS RESULTS (from NLP analysis):
{semantic_context}

ANALYSIS PROTOCOL:
Step 1. CLAIM EXTRACTION: Identify 2-4 atomic claims in the backstory (e.g., "character has trait X", "character experienced event Y", "character relationship Z")
Step 2. DETAIL VERIFICATION: Check if specific entities (names, places) and dates mentioned in backstory actually appear in evidence
Step 3. EVIDENCE MAPPING: For each claim, map it to supporting/contradicting evidence pieces
Step 4. SEMANTIC VERIFICATION: Cross-reference with semantic analysis context - trust high support scores and explicit contradictions
Step 5. SCORING CALCULATION:
  - Support score >= 0.75 AND detail_overlap > 0.5: Strong alignment (CONSISTENT, 0.90-0.95 confidence)
  - Support score 0.60-0.75 AND no contradictions: Moderate alignment (CONSISTENT, 0.80-0.89 confidence)
  - Support score 0.40-0.60 AND ambiguous: Weak alignment (INCONCLUSIVE, 0.55-0.70 confidence)
  - Support score < 0.40 OR contradictions found OR detail_overlap < 0.25: Misalignment (INCONSISTENT, 0.85-0.95 confidence)
Step 6. CAUSAL CHECK: If causal consistency score >= 0.8, add +0.05 to confidence (max 0.95)

CRITICAL ANTI-HALLUCINATION RULES (highest priority):
1. DO NOT HALLUCINATE SUPPORT: If specific names, dates (e.g., 1852), or unique objects (e.g., 'oak barrels') are in the backstory but NOT in the evidence, you MUST mark it as INCONSISTENT (0) with high confidence (0.85-0.95)
2. IGNORE VAGUE THEMATIC OVERLAP: Just because the backstory mentions "prison" and evidence mentions "prison" does not mean they match if the specific events/characters differ
3. DETECT TIMELINE CONTRADICTIONS: If backstory says character was in place X in year Y, but evidence says they were in place Z, mark as 0
4. VERIFY SPECIFIC EVENTS: If backstory claims a specific event (e.g., "saved 8 survivors") that is never mentioned in the novel, mark as 0
5. MISSING DETAILS OVERRIDE: If the Missing Details Warning shows 2+ specific details absent from evidence, this is strong evidence of hallucination → predict 0

ABSOLUTE DECISION RULES (apply in order):
1. If Missing Details Warning shows detail_overlap < 0.25 AND total_details >= 2: HALLUCINATION → Predict 0 with 0.90-0.95 confidence
2. If explicit contradictions detected AND high support exists: CONTRADICTION overrides support → Predict 0 with 0.90-0.95 confidence
3. If support_score >= 0.75 AND detail_overlap > 0.5 AND no contradictions: Predict 1 with 0.90-0.95 confidence
4. If support_score >= 0.60 AND causal_consistency >= 0.75 AND no contradictions: Predict 1 with 0.85-0.90 confidence
5. If support_score 0.40-0.60 AND ambiguous: Predict 0 with 0.65-0.75 confidence (default to inconsistent for weak evidence)
6. If no evidence OR support_score < 0.40: Predict 0 with 0.80-0.90 confidence

TONE INSTRUCTION: Be confident in your judgment. Use the high-confidence ranges (0.85+) when you have semantic analysis backing your decision. Be especially confident when detecting hallucinations.

REQUIRED OUTPUT FORMAT (strict):
JUDGMENT: [0 or 1]
CONFIDENCE: [0.80-0.95 range preferred, minimum 0.55]
REASONING: [Exactly 3-4 sentences showing: (1) main claims found, (2) detail verification results, (3) key evidence alignment/contradiction, (4) final confidence justification]

Begin analysis:"""
        
        return prompt
    
    def _judge_with_llm(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        LLM-based consistency checking using Cerebras (Llama 3.1 8B).
        """
        try:
            # Prepare evidence context
            evidence_text = self._format_evidence_for_llm(evidence)
            prompt = self._create_judgment_prompt(backstory, evidence_text)
            
            # Initialize Cerebras Client
            api_key = os.getenv('CEREBRAS_API_KEY')
            if not api_key:
                logger.error("CEREBRAS_API_KEY not found. Please add it to .env")
                return self._judge_with_heuristics(backstory, evidence, novel_id)

            client = OpenAI(
                api_key=api_key,
                base_url="https://api.cerebras.ai/v1"
            )
            
            response = client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model="llama3.1-8b", 
                temperature=0,
                max_tokens=1000,
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            prediction, rationale, confidence = self._parse_llm_response(response_text)
            
            logger.info(f"LLM judgment for {novel_id}: {prediction} (confidence: {confidence:.2f})")
            return prediction, rationale, confidence
            
        except Exception as e:
            logger.error(f"Error in LLM judgment: {e}")
            return self._judge_with_heuristics(backstory, evidence, novel_id)
    
    def _format_evidence_for_llm(self, evidence: List[Dict], max_chunks: int = 15) -> str:
        """
        Format evidence chunks for LLM consumption.
        """
        formatted_pieces = []
        
        for i, chunk in enumerate(evidence[:max_chunks], 1):
            formatted_pieces.append(
                f"[Evidence {i}] (Relevance: {chunk['similarity']:.2f})\n"
                f"{chunk['text']}\n"
            )
        
        return "\n".join(formatted_pieces)
    
    def _create_judgment_prompt(self, backstory: str, evidence_text: str) -> str:
        """
        Create prompt for Llama 3 judgment (basic version without semantic enhancement).
        """
        prompt = f"""You are analyzing narrative consistency in a novel.
        
BACKSTORY TO EVALUATE:
{backstory}

EVIDENCE FROM NOVEL:
{evidence_text}

TASK:
Determine if this backstory is CONSISTENT (1) or INCONSISTENT (0) with the novel based on the evidence.

IMPORTANT GUIDELINES:
1. Focus on CAUSAL CONSISTENCY and SPECIFIC DETAILS.
2. If the evidence directly contradicts the backstory (e.g. backstory says "rich", novel says "poverty"), mark as 0.
3. If specific names, dates, or events in backstory are NOT mentioned in evidence, mark as 0.
4. If the backstory is plausible, supported by evidence, and not contradicted, mark as 1.

REQUIRED OUTPUT FORMAT:
JUDGMENT: [0 or 1]
CONFIDENCE: [0.0-1.0]
REASONING: [2-3 sentence explanation of your decision]

Provide your analysis now:"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str) -> Tuple[int, str, float]:
        """
        Parse structured output from LLM.
        """
        # Extract judgment
        judgment_match = re.search(r'JUDGMENT:\s*(\d)', response_text)
        if judgment_match:
            prediction = int(judgment_match.group(1))
        else:
            # Fallback: look for keywords
            if 'inconsistent' in response_text.lower():
                prediction = 0
            else:
                prediction = 1
        
        # Extract confidence
        confidence_match = re.search(r'CONFIDENCE:\s*(0?\.\d+|1\.0)', response_text)
        if confidence_match:
            confidence = float(confidence_match.group(1))
        else:
            confidence = 0.85  # Default high confidence
        
        # Extract reasoning
        reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n\n|$)', response_text, re.DOTALL)
        if reasoning_match:
            rationale = reasoning_match.group(1).strip()
        else:
            # Fallback: use the whole response
            rationale = response_text[:200] + "..." if len(response_text) > 200 else response_text
        
        return prediction, rationale, confidence
    
    def batch_judge(
        self,
        backstory_evidence_pairs: List[Tuple[str, List[Dict], str]]
    ) -> List[Dict]:
        """
        Process multiple backstory-evidence pairs efficiently.
        """
        results = []
        total = len(backstory_evidence_pairs)
        
        logger.info(f"Processing {total} consistency judgments...")
        
        for i, (backstory, evidence, novel_id) in enumerate(backstory_evidence_pairs, 1):
            logger.info(f"Judging {i}/{total}: {novel_id}")
            
            prediction, rationale, confidence = self.judge_consistency(
                backstory, evidence, novel_id
            )
            
            results.append({
                'novel_id': novel_id,
                'prediction': prediction,
                'rationale': rationale,
                'confidence': confidence
            })
            
            # Add a small delay if using LLM to respect rate limits
            if self.use_llm and i < total:
                time.sleep(0.2)
        
        logger.info("Batch judgment complete")
        return results


if __name__ == "__main__":
    # Test the judge with mock evidence
    judge = ConsistencyJudge(use_llm=False)
    
    # TEST CASE 1: Contradiction (Wealth vs Poverty)
    print("\nTest Case 1: Contradiction")
    test_backstory_1 = "John was born wealthy and inherited a private hospital."
    test_evidence_1 = [
        {
            'text': "John remembered the cold winters in his childhood home, where heating was a luxury they couldn't afford due to their extreme poverty.",
            'similarity': 0.85
        }
    ]
    pred1, rat1, conf1 = judge.judge_consistency(test_backstory_1, test_evidence_1, "test1")
    print(f"Prediction: {pred1} (Expected: 0)")
    print(f"Confidence: {conf1:.2f}")
    print(f"Rationale: {rat1}")

    # TEST CASE 2: Consistent
    print("\nTest Case 2: Consistent")
    test_backstory_2 = "John grew up in poverty in London."
    test_evidence_2 = [
        {
            'text': "John remembered the cold winters in his childhood home in London, where heating was a luxury they couldn't afford.",
            'similarity': 0.85
        }
    ]
    pred2, rat2, conf2 = judge.judge_consistency(test_backstory_2, test_evidence_2, "test2")
    print(f"Prediction: {pred2} (Expected: 1)")
    print(f"Confidence: {conf2:.2f}")
    print(f"Rationale: {rat2}")
    
    # TEST CASE 3: Hallucination Detection
    print("\nTest Case 3: Hallucination (Specific details missing)")
    test_backstory_3 = "John Smith was born in 1852 in Manchester and worked at the Royal Hospital."
    test_evidence_3 = [
        {
            'text': "The young man grew up in England and later became a doctor.",
            'similarity': 0.65
        }
    ]
    pred3, rat3, conf3 = judge.judge_consistency(test_backstory_3, test_evidence_3, "test3")
    print(f"Prediction: {pred3} (Expected: 0 - hallucinated details)")
    print(f"Confidence: {conf3:.2f}")
    print(f"Rationale: {rat3}")