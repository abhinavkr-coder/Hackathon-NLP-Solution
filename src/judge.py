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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsistencyJudge:
    def __init__(self, use_llm: bool = True, api_key: str = None):
        self.use_llm = use_llm
        self.api_key = api_key

        if use_llm and not api_key:
            # Changed from ANTHROPIC_API_KEY to CEREBRAS_API_KEY
            self.api_key = os.getenv('CEREBRAS_API_KEY')
            if not self.api_key:
                logger.warning(
                    "No API key provided and CEREBRAS_API_KEY not in environment. "
                    "Falling back to rule-based judgment."
                )
                self.use_llm = False

    # ---------------------------------------------------------
    # MAIN ENTRY POINTS
    # ---------------------------------------------------------

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
        if not evidence:
            return 0, "No evidence found in the novel to support this backstory.", 0.0
        if self.use_llm:
            return self._judge_with_llm(backstory, evidence, novel_id)
        return self._judge_with_heuristics(backstory, evidence, novel_id)

    def judge_with_temporal_constraints(
        self,
        backstory: str,
        temporal_evidence: Dict[str, List[Dict]],
        novel_id: str
    ) -> Tuple[int, str, float]:
        """
        Track-A core logic.
        Enforces narrative constraints over time.
        """

        early = temporal_evidence.get("early", [])
        middle = temporal_evidence.get("middle", [])
        late = temporal_evidence.get("late", [])

        # HARD RULE: early contradiction kills backstory
        if self._has_contradiction(backstory, early, min_similarity=0.6):
            return 0, "Early narrative contradicts backstory constraints", 0.9

        # LATE contradiction only matters if unsupported earlier
        if self._has_contradiction(backstory, late, min_similarity=0.7):
            if not self._has_support(early + middle):
                return 0, "Later events conflict with unsupported backstory", 0.7

        # Positive support anywhere without contradiction
        if self._has_support(early + middle + late):
            return 1, "Backstory remains consistent across narrative timeline", 0.8

        return 0, "Insufficient narrative support for backstory", 0.6

    # ---------------------------------------------------------
    # SUPPORT / CONTRADICTION DETECTORS
    # ---------------------------------------------------------

    def _has_contradiction(
        self,
        backstory: str,
        evidence: List[Dict],
        min_similarity: float
    ) -> bool:
        negation_words = {
            "not", "never", "no", "nothing",
            "nobody", "impossible", "cannot"
        }

        backstory_words = set(backstory.lower().split())

        for chunk in evidence:
            if chunk.get("similarity", 0) < min_similarity:
                continue

            text = chunk.get("text", "").lower()
            text_words = set(text.split())

            # Antonym contradiction
            if self._check_antonyms(backstory, text):
                return True

            # Negation overlap
            if len(backstory_words & text_words) > 3:
                if any(n in text_words for n in negation_words):
                    return True

        return False

    def _has_support(self, evidence: List[Dict]) -> bool:
        for chunk in evidence:
            if chunk.get("similarity", 0) >= 0.65:
                return True
        return False

    def _check_antonyms(self, backstory: str, evidence_text: str) -> bool:
        pairs = [
            ("wealthy", "poverty"), ("rich", "poor"),
            ("aristocrat", "peasant"), ("noble", "commoner"),
            ("loved", "hated"), ("always", "never"),
            ("brave", "cowardly"), ("strong", "weak"),
            ("dead", "alive"), ("died", "survived")
        ]

        b = backstory.lower()
        e = evidence_text.lower()

        for w1, w2 in pairs:
            if (w1 in b and w2 in e) or (w2 in b and w1 in e):
                return True
        return False

    # ---------------------------------------------------------
    # HEURISTIC + LLM FALLBACKS (UNCHANGED)
    # ---------------------------------------------------------

    def _judge_with_heuristics(
        self,
        backstory: str,
        evidence: List[Dict],
        novel_id: str
    ) -> Tuple[int, str, float]:

        if not evidence:
            return 0, "No evidence found to support backstory", 0.5

        avg_similarity = sum(c["similarity"] for c in evidence) / len(evidence)
        combined_text = " ".join(c["text"] for c in evidence)

        if self._check_antonyms(backstory, combined_text):
            return 0, "Backstory contradicts narrative evidence", 0.8

        if avg_similarity > 0.65:
            return 1, "Backstory is broadly supported by narrative", 0.75

        return 0, "Insufficient evidence to confirm backstory", 0.5

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
            # It uses the OpenAI SDK but points to Cerebras URL
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
                # Use "llama3.1-8b" for best speed/free-tier limits
                model="llama3.1-8b", 
                temperature=0,
                max_tokens=800
            )

            return self._parse_llm_response(
                response.choices[0].message.content
            )

        except Exception as e:
            logger.error(f"LLM failure: {e}")
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

EVIDENCE:
{evidence}

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