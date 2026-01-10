from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
import logging
import os
import re
import time
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsistencyJudge:
    def __init__(self, use_llm: bool = True, api_key: str = None):
        self.use_llm = use_llm
        self.api_key = api_key

        if use_llm and not api_key:
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                logger.warning(
                    "No GROQ_API_KEY found. Falling back to heuristic mode."
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
        try:
            from groq import Groq

            prompt = self._create_judgment_prompt(
                backstory,
                self._format_evidence_for_llm(evidence)
            )

            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0,
                max_tokens=800
            )

            return self._parse_llm_response(
                response.choices[0].message.content
            )

        except Exception as e:
            logger.error(f"LLM failure: {e}")
            return self._judge_with_heuristics(backstory, evidence, novel_id)

    # ---------------------------------------------------------
    # LLM HELPERS
    # ---------------------------------------------------------

    def _format_evidence_for_llm(self, evidence: List[Dict]) -> str:
        return "\n\n".join(
            f"[{i+1}] ({c['similarity']:.2f}) {c['text']}"
            for i, c in enumerate(evidence[:15])
        )

    def _create_judgment_prompt(self, backstory: str, evidence: str) -> str:
        return f"""
BACKSTORY:
{backstory}

EVIDENCE:
{evidence}

Decide if the backstory is CONSISTENT (1) or INCONSISTENT (0).
Focus on causal and temporal consistency.

Output format:
JUDGMENT: <0 or 1>
CONFIDENCE: <0.0–1.0>
REASONING: <brief>
"""

    def _parse_llm_response(self, text: str) -> Tuple[int, str, float]:
        pred = 1
        if "JUDGMENT:" in text:
            pred = int(re.search(r"JUDGMENT:\s*(\d)", text).group(1))

        conf = 0.7
        m = re.search(r"CONFIDENCE:\s*(0?\.\d+|1\.0)", text)
        if m:
            conf = float(m.group(1))

        reason = text.strip()[:200]
        return pred, reason, conf
