"""
retrieve.py - Intelligent Evidence Retrieval

This module implements sophisticated retrieval strategies for finding narrative
evidence. The challenge isn't just finding text that matches keywords - it's
finding passages that establish constraints, reveal character development,
or show causal relationships.

Think of this as a legal investigation: we need to find evidence that either
supports or contradicts the backstory claim, not just passages that mention
the same topics.
"""

import logging
from typing import List, Dict, Tuple
from embeddings import PathwayVectorStore, EmbeddingManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """
    Retrieves relevant evidence from novels using multiple strategies.
    
    The core insight: Different types of backstory claims require different
    retrieval approaches. A claim about a character's childhood trauma needs
    different evidence than a claim about their profession.
    """
    
    def __init__(self, vector_store: PathwayVectorStore):
        self.vector_store = vector_store
    
    def decompose_backstory(self, backstory: str) -> List[str]:
        """
        Break a backstory into atomic claims that can be individually verified.
        
        A backstory like "John grew up poor in London and became a doctor to
        help his community" contains multiple claims:
        1. John grew up in poverty
        2. John grew up in London
        3. John became a doctor
        4. His motivation was helping the community
        
        Each needs to be checked against the novel independently.
        
        For now, we use a simple sentence-based decomposition. In a more
        sophisticated system, you could use an LLM to extract claims.
        """
        # Simple approach: split by sentences and major connecting words
        import re
        
        # Split on periods, semicolons, and coordinating conjunctions
        potential_claims = re.split(r'[.;]|\band\b|\bbut\b|\byet\b', backstory)
        
        # Clean and filter
        claims = [
            claim.strip()
            for claim in potential_claims
            if claim.strip() and len(claim.strip().split()) > 3
        ]
        
        # Always include the full backstory as a holistic claim
        claims.append(backstory)
        
        return claims
    
    def retrieve_for_backstory(
        self,
        backstory: str,
        novel_id: str,
        top_k: int = 15
    ) -> List[Dict]:
        """
        Retrieve evidence relevant to an entire backstory.
        
        This is our main entry point. We use a multi-pronged approach:
        1. Break backstory into claims
        2. Search for each claim
        3. Aggregate and diversify results
        4. Rank by relevance
        """
        logger.info(f"Retrieving evidence for novel {novel_id}")
        
        # Decompose backstory into verifiable claims
        claims = self.decompose_backstory(backstory)
        logger.info(f"Extracted {len(claims)} claims from backstory")
        
        # Retrieve for each claim
        all_chunks = self.vector_store.multi_query_search(
            queries=claims,
            novel_id=novel_id,
            top_k_per_query=max(3, top_k // len(claims))
        )
        
        # Take top-k overall
        evidence = all_chunks[:top_k]
        
        logger.info(f"Retrieved {len(evidence)} evidence chunks")
        return evidence
    
    def retrieve_with_character_focus(
        self,
        backstory: str,
        character_name: str,
        novel_id: str,
        top_k: int = 15
    ) -> List[Dict]:
        """
        Retrieve evidence with special attention to character-specific passages.
        
        When we know which character the backstory is about, we can do better:
        - Weight passages that mention the character more heavily
        - Look for character actions, dialogue, and descriptions
        - Find passages showing character evolution over time
        """
        # First, get base evidence
        evidence = self.retrieve_for_backstory(backstory, novel_id, top_k * 2)
        
        # Re-rank based on character mentions
        for chunk in evidence:
            # Count character mentions (case-insensitive)
            text_lower = chunk['text'].lower()
            char_lower = character_name.lower()
            mention_count = text_lower.count(char_lower)
            
            # Boost similarity score based on mentions
            # This ensures character-relevant passages rank higher
            chunk['adjusted_similarity'] = (
                chunk['similarity'] * (1 + 0.1 * mention_count)
            )
        
        # Re-sort and return top-k
        evidence.sort(key=lambda x: x['adjusted_similarity'], reverse=True)
        return evidence[:top_k]
    
    def retrieve_temporal_evidence(
        self,
        backstory: str,
        novel_id: str,
        top_k: int = 15
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve evidence organized by narrative position.
        
        This is crucial for consistency checking. Events early in a novel
        establish constraints that must hold later. We need to check if:
        1. Early passages contradict the backstory
        2. Middle passages show development consistent with the backstory
        3. Late passages reach outcomes that make sense given the backstory
        
        Returns evidence grouped by narrative position: early, middle, late.
        """
        # Get base evidence
        all_evidence = self.retrieve_for_backstory(backstory, novel_id, top_k * 2)
        
        # We need to know the total number of chunks in the novel to calculate position
        # For this, we look at chunk_ids (assuming they're sequential)
        max_chunk_id = max(
            chunk['chunk_id']
            for chunk in self.vector_store.chunks
            if chunk['novel_id'] == novel_id
        )
        
        # Categorize by position
        temporal_evidence = {
            'early': [],    # First third
            'middle': [],   # Middle third
            'late': []      # Final third
        }
        
        for chunk in all_evidence:
            position = chunk['chunk_id'] / max_chunk_id
            
            if position < 0.33:
                temporal_evidence['early'].append(chunk)
            elif position < 0.66:
                temporal_evidence['middle'].append(chunk)
            else:
                temporal_evidence['late'].append(chunk)
        
        # Ensure we have balanced representation
        # This prevents us from only seeing evidence from one part of the story
        for period in temporal_evidence:
            temporal_evidence[period] = temporal_evidence[period][:top_k // 3]
        
        logger.info(
            f"Retrieved evidence: {len(temporal_evidence['early'])} early, "
            f"{len(temporal_evidence['middle'])} middle, "
            f"{len(temporal_evidence['late'])} late"
        )
        
        return temporal_evidence
    
    def retrieve_causal_chain(
        self,
        backstory: str,
        novel_id: str,
        top_k: int = 15
    ) -> List[Dict]:
        """
        Retrieve evidence showing causal relationships and constraints.
        
        This addresses the core challenge: finding passages that show not just
        what happened, but WHY it happened and what it prevented from happening.
        
        We look for:
        - Explicit causal language ("because", "therefore", "as a result")
        - Character motivations and decision points
        - Moments where past events constrain future possibilities
        """
        # Get base evidence
        evidence = self.retrieve_for_backstory(backstory, novel_id, top_k * 2)
        
        # Keywords that often indicate causal relationships or constraints
        causal_indicators = [
            'because', 'therefore', 'thus', 'consequently', 'as a result',
            'due to', 'caused by', 'led to', 'resulted in',
            'motivated', 'driven by', 'compelled', 'forced',
            'couldn\'t', 'impossible', 'prevented', 'forbade',
            'had to', 'must', 'required', 'necessary'
        ]
        
        # Score chunks based on causal language
        for chunk in evidence:
            text_lower = chunk['text'].lower()
            causal_score = sum(
                1 for indicator in causal_indicators
                if indicator in text_lower
            )
            
            # Boost similarity for chunks with causal language
            chunk['causal_boosted_similarity'] = (
                chunk['similarity'] * (1 + 0.15 * causal_score)
            )
        
        # Re-sort and return top-k
        evidence.sort(key=lambda x: x['causal_boosted_similarity'], reverse=True)
        return evidence[:top_k]


class ConstraintExtractor:
    """
    Extracts narrative constraints from retrieved evidence.
    
    This is where we move from "here's relevant text" to "here's what this
    text tells us must or cannot be true about the backstory."
    """
    
    @staticmethod
    def extract_character_constraints(evidence: List[Dict], character_name: str) -> List[str]:
        """
        Extract what the evidence tells us MUST be true about a character.
        
        These are hard constraints - things that directly contradict or support
        specific claims in the backstory.
        """
        constraints = []
        
        for chunk in evidence:
            text = chunk['text']
            
            # Look for passages that describe the character
            if character_name.lower() in text.lower():
                # This is simplified - in reality, you'd use dependency parsing
                # or an LLM to extract structured information
                constraints.append({
                    'text': text,
                    'similarity': chunk['similarity'],
                    'type': 'character_description'
                })
        
        return constraints
    
    @staticmethod
    def identify_contradictions(
        evidence: List[Dict],
        backstory_claims: List[str]
    ) -> List[Tuple[str, str, float]]:
        """
        Identify potential contradictions between evidence and backstory claims.
        
        Returns list of (evidence_text, claim, confidence) tuples where the
        evidence might contradict the claim.
        
        This is a simplified heuristic approach. A production system would
        use an NLI (Natural Language Inference) model here.
        """
        potential_contradictions = []
        
        # This is where you'd implement sophisticated contradiction detection
        # For now, we flag high-similarity passages for manual review
        for chunk in evidence:
            for claim in backstory_claims:
                # High similarity but containing negation words might indicate contradiction
                negation_words = ['not', 'never', 'no', 'none', 'nobody', 'nothing']
                has_negation = any(word in chunk['text'].lower() for word in negation_words)
                
                if chunk['similarity'] > 0.7 and has_negation:
                    potential_contradictions.append((
                        chunk['text'],
                        claim,
                        chunk['similarity']
                    ))
        
        return potential_contradictions


if __name__ == "__main__":
    # Test the retrieval system
    print("Retrieval module loaded. Use main.py to run full pipeline.")