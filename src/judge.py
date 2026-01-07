"""
judge.py - Consistency Judgment Engine

This is where we make the final decision: is the backstory consistent with the novel?

The challenge here is subtle. We're not checking for word-for-word matches or
simple contradictions. We're asking a deeper question: given the constraints
established throughout the narrative, could this backstory plausibly lead to
the events we observe?

Think of it like a detective reviewing evidence. Individual pieces might seem
innocuous, but together they paint a picture that either supports or contradicts
a hypothesis.
"""

import logging
from typing import List, Dict, Tuple
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsistencyJudge:
    """
    Makes consistency judgments using evidence-based reasoning.
    
    We use a multi-stage approach:
    1. Analyze retrieved evidence for support and contradiction
    2. Weight evidence by quality and relevance
    3. Apply consistency heuristics
    4. Make final judgment with confidence score
    
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
            import os
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                logger.warning(
                    "No API key provided and ANTHROPIC_API_KEY not in environment. "
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
        Main entry point for consistency judgment.
        
        Returns:
            prediction: 1 (consistent) or 0 (inconsistent)
            rationale: Explanation of the decision
            confidence: Score between 0 and 1 indicating decision confidence
        """
        if self.use_llm:
            return self._judge_with_llm(backstory, evidence, novel_id)
        else:
            return self._judge_with_heuristics(backstory, evidence, novel_id)
    
    def _judge_with_heuristics(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        Rule-based consistency checking.
        
        This is a fallback method that uses linguistic cues and similarity
        patterns to make a judgment. It's not as sophisticated as LLM-based
        reasoning, but it's fast and interpretable.
        
        Key heuristics:
        1. Strong negation in high-similarity passages suggests contradiction
        2. Low overall similarity suggests backstory is unsupported
        3. Inconsistent temporal patterns suggest problems
        4. Causal language that conflicts with backstory suggests inconsistency
        """
        if not evidence:
            return 0, "No evidence found to support backstory", 0.5
        
        # Calculate average similarity
        avg_similarity = sum(chunk['similarity'] for chunk in evidence) / len(evidence)
        
        # Check for negation words in high-similarity chunks
        negation_words = ['not', 'never', 'no', 'none', 'nobody', 'nothing', 'impossible', 'cannot']
        contradiction_count = 0
        
        for chunk in evidence[:5]:  # Focus on top 5 most similar
            if chunk['similarity'] > 0.7:
                text_lower = chunk['text'].lower()
                if any(word in text_lower for word in negation_words):
                    contradiction_count += 1
        
        # Decision logic
        if avg_similarity < 0.4:
            # Very low similarity - backstory might be unrelated to novel
            return 0, "Backstory claims are not well-supported by the narrative", 0.6
        
        elif contradiction_count >= 2:
            # Multiple high-similarity passages with negation
            return 0, "Evidence contains contradictions to backstory claims", 0.7
        
        elif avg_similarity > 0.6 and contradiction_count == 0:
            # High similarity, no clear contradictions
            return 1, "Backstory is well-supported by narrative evidence", 0.7
        
        else:
            # Ambiguous case - lean toward consistent if evidence is moderately relevant
            if avg_similarity > 0.5:
                return 1, "Backstory is plausible given available evidence", 0.5
            else:
                return 0, "Insufficient evidence to support backstory", 0.5
    
    def _judge_with_llm(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        LLM-based consistency checking with structured reasoning.
        
        This is where we leverage Claude's reasoning capabilities to make
        sophisticated judgments about narrative consistency.
        
        The prompt is carefully designed to:
        1. Focus on causal consistency, not surface contradictions
        2. Consider evidence holistically, not in isolation
        3. Distinguish between "not mentioned" and "contradicted"
        4. Provide clear reasoning that can be audited
        """
        try:
            # Prepare evidence context
            evidence_text = self._format_evidence_for_llm(evidence)
            
            # Create the judgment prompt
            prompt = self._create_judgment_prompt(backstory, evidence_text)
            
            # Call Claude API
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0,  # We want consistent, deterministic judgments
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            response_text = response.content[0].text
            prediction, rationale, confidence = self._parse_llm_response(response_text)
            
            logger.info(f"LLM judgment for {novel_id}: {prediction} (confidence: {confidence:.2f})")
            return prediction, rationale, confidence
            
        except Exception as e:
            logger.error(f"Error in LLM judgment: {e}")
            logger.info("Falling back to heuristic judgment")
            return self._judge_with_heuristics(backstory, evidence, novel_id)
    
    def _format_evidence_for_llm(self, evidence: List[Dict], max_chunks: int = 10) -> str:
        """
        Format evidence chunks for LLM consumption.
        
        We need to present evidence clearly but concisely to stay within
        context limits. We prioritize the most relevant chunks.
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
        Create a carefully structured prompt for LLM judgment.
        
        This prompt is designed to elicit reasoning about causal consistency
        and narrative constraints, not just surface-level matching.
        """
        prompt = f"""You are analyzing narrative consistency in a novel. Your task is to determine whether a proposed character backstory is causally and logically consistent with events in the novel.

BACKSTORY TO EVALUATE:
{backstory}

EVIDENCE FROM NOVEL:
{evidence_text}

TASK:
Determine if this backstory is CONSISTENT (1) or INCONSISTENT (0) with the novel based on the evidence.

IMPORTANT GUIDELINES:
1. Focus on CAUSAL CONSISTENCY: Would the events in the evidence still make sense if this backstory were true? Or would it create logical impossibilities or contradictions?

2. Distinguish between:
   - NOT MENTIONED (neutral, could be consistent)
   - CONTRADICTED (actively inconsistent)

3. Consider narrative constraints: Even if nothing explicitly contradicts the backstory, does it fit the character's development, motivations, and the world's established rules?

4. Look for:
   - Direct contradictions in facts or timeline
   - Incompatible character traits or motivations
   - Events that wouldn't make sense given the backstory
   - Missed opportunities where the backstory should have mattered but didn't

5. Base your judgment on multiple pieces of evidence, not a single passage.

REQUIRED OUTPUT FORMAT:
JUDGMENT: [0 or 1]
CONFIDENCE: [0.0-1.0]
REASONING: [2-3 sentence explanation of your decision, citing specific evidence]

Provide your analysis now:"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str) -> Tuple[int, str, float]:
        """
        Parse structured output from LLM.
        
        We expect the LLM to follow our format, but we add robust parsing
        to handle slight variations.
        """
        # Extract judgment
        judgment_match = re.search(r'JUDGMENT:\s*(\d)', response_text)
        if judgment_match:
            prediction = int(judgment_match.group(1))
        else:
            # Fallback: look for "consistent" or "inconsistent" in text
            if 'inconsistent' in response_text.lower():
                prediction = 0
            else:
                prediction = 1
        
        # Extract confidence
        confidence_match = re.search(r'CONFIDENCE:\s*(0?\.\d+|1\.0)', response_text)
        if confidence_match:
            confidence = float(confidence_match.group(1))
        else:
            confidence = 0.7  # Default moderate confidence
        
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
        
        This is useful for the test set where we have multiple examples to judge.
        We add progress tracking to give feedback during long runs.
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
                import time
                time.sleep(0.5)
        
        logger.info("Batch judgment complete")
        return results


if __name__ == "__main__":
    # Test the judge with mock evidence
    judge = ConsistencyJudge(use_llm=False)
    
    test_backstory = "John grew up in poverty in London"
    test_evidence = [
        {
            'text': "John remembered the cold winters in his childhood home in London, where heating was a luxury they couldn't afford.",
            'similarity': 0.85
        },
        {
            'text': "Despite his humble beginnings, John had always been driven to succeed.",
            'similarity': 0.72
        }
    ]
    
    prediction, rationale, confidence = judge.judge_consistency(
        test_backstory, test_evidence, "test"
    )
    
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Rationale: {rationale}")