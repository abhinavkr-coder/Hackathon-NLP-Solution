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
import os
import re
import time
from typing import List, Dict, Tuple

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
            # Changed from ANTHROPIC_API_KEY to GROQ_API_KEY
            self.api_key = os.getenv('GROQ_API_KEY')
            if not self.api_key:
                logger.warning(
                    "No API key provided and GROQ_API_KEY not in environment. "
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
            # Ambiguous case - Default to UNCERTAIN/INCONSISTENT if not strongly supported
            # (Changed from returning 1 to 0 to avoid false positives)
            if avg_similarity > 0.6:
                return 1, "Backstory is plausible given available evidence", 0.55
            else:
                return 0, "Insufficient evidence to confirm backstory", 0.5
    
    def _judge_with_llm(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        LLM-based consistency checking using a supported Llama model (via Groq).
        """
        try:
            # Prepare evidence context
            evidence_text = self._format_evidence_for_llm(evidence)
            prompt = self._create_judgment_prompt(backstory, evidence_text)
            
            # Import Groq client
            from groq import Groq
            client = Groq(api_key=self.api_key)
            
            response = client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                # UPDATED: Use a supported model like llama-3.3-70b-versatile
                model="llama-3.3-70b-versatile", 
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
        Create prompt for Llama 3 judgment.
        """
        prompt = f"""You are analyzing narrative consistency in a novel.
        
BACKSTORY TO EVALUATE:
{backstory}

EVIDENCE FROM NOVEL:
{evidence_text}

TASK:
Determine if this backstory is CONSISTENT (1) or INCONSISTENT (0) with the novel based on the evidence.

IMPORTANT GUIDELINES:
1. Focus on CAUSAL CONSISTENCY.
2. If the evidence directly contradicts the backstory (e.g. backstory says "rich", novel says "poverty"), mark as 0.
3. If the backstory is plausible and not contradicted, mark as 1.

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
                time.sleep(0.5)
        
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
    print(f"Rationale: {rat2}")