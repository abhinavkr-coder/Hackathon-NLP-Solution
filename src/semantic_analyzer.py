"""
semantic_analyzer.py - Advanced Semantic Analysis for Better Consistency Checking

This module provides enhanced semantic understanding for narrative consistency evaluation.
It goes beyond simple keyword matching to understand causal relationships, character
motivations, and narrative constraints.
"""

import re
import logging
from typing import List, Dict, Tuple, Set
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    Advanced semantic analysis for narrative consistency checking.
    
    Capabilities:
    1. Causal relationship detection
    2. Character motivation extraction
    3. Narrative constraint identification
    4. Semantic contradiction analysis
    5. Entity and Fact Verification (Anti-Hallucination)
    """
    
    def __init__(self):
        """Initialize semantic analyzer with linguistic patterns."""
        self.causal_indicators = {
            'because', 'therefore', 'thus', 'consequently', 'as a result',
            'due to', 'caused by', 'led to', 'resulted in', 'caused',
            'motivated', 'driven by', 'compelled', 'forced', 'driven',
            'couldn\'t', 'impossible', 'prevented', 'forbade', 'prohibition',
            'had to', 'must', 'required', 'necessary', 'essential',
            'forced to', 'obligated', 'compelled to', 'forced to act'
        }
        
        self.antonym_pairs = [
            ('wealthy', 'poverty'), ('rich', 'poor'), ('wealth', 'impoverished'),
            ('aristocrat', 'peasant'), ('noble', 'commoner'), ('upper', 'lower'),
            ('loved', 'hated'), ('affection', 'hatred'), ('adored', 'despised'),
            ('brave', 'cowardly'), ('courageous', 'fearful'), ('valor', 'fear'),
            ('strong', 'weak'), ('powerful', 'powerless'), ('vigor', 'frail'),
            ('dead', 'alive'), ('died', 'survived'), ('deceased', 'living'),
            ('murdered', 'survived'), ('killed', 'lived'), ('fatal', 'survival'),
            ('trusted', 'betrayed'), ('loyal', 'traitor'), ('faithful', 'disloyal'),
            ('helped', 'harmed'), ('aid', 'harm'), ('assistance', 'sabotage')
        ]

        # Common stop words to filter out from entity extraction
        self.stop_words = {
            'The', 'A', 'An', 'He', 'She', 'It', 'They', 'We', 'I', 'You',
            'This', 'That', 'These', 'Those', 'In', 'On', 'At', 'To', 'For',
            'Of', 'By', 'With', 'From', 'After', 'Before', 'While', 'When',
            'Where', 'Who', 'What', 'Why', 'How', 'Then', 'So', 'But', 'And',
            'Or', 'Nor', 'Yet', 'Once', 'Since', 'Although', 'Though'
        }
    
    def analyze_backstory_claims(self, backstory: str) -> List[Dict]:
        """
        Extract and analyze individual claims from backstory.
        
        Returns list of dicts with:
        - text: The extracted claim
        - type: 'character_trait', 'event', 'motivation', 'relationship'
        - importance: 'high', 'medium', 'low'
        - entities: List of named entities
        - dates: List of extracted dates
        - actions: List of action verbs
        """
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', backstory)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence.split()) < 3:
                continue
            
            claim_dict = {
                'text': sentence,
                'type': self._classify_claim(sentence),
                'importance': self._assess_importance(sentence),
                'entities': self._extract_entities(sentence),
                'dates': self._extract_dates(sentence),
                'actions': self._extract_actions(sentence)
            }
            claims.append(claim_dict)
        
        return claims
    
    def calculate_detail_overlap(self, backstory: str, evidence: List[Dict]) -> Dict:
        """
        Calculate how many specific details (Entities, Dates) from the backstory 
        actually appear in the evidence. This is crucial for detecting hallucinations.
        
        Returns dict with:
        - overlap_score: Float 0-1 representing detail overlap
        - found_count: Number of details found in evidence
        - total_details: Total number of details in backstory
        - missing_details: List of details not found in evidence
        """
        bs_entities = set(self._extract_entities(backstory))
        bs_dates = set(self._extract_dates(backstory))
        
        if not bs_entities and not bs_dates:
            return {
                'overlap_score': 0.5,
                'found_count': 0,
                'total_details': 0,
                'missing_details': []
            }  # No details to verify
            
        combined_evidence = " ".join([e['text'].lower() for e in evidence])
        
        found_entities = 0
        missing_details = []
        
        # Check Entities
        for entity in bs_entities:
            # Simple check: is the entity string in the evidence?
            if entity.lower() in combined_evidence:
                found_entities += 1
            else:
                missing_details.append(entity)
                
        # Check Dates
        found_dates = 0
        for date in bs_dates:
            if date in combined_evidence:
                found_dates += 1
            else:
                missing_details.append(date)
        
        total_details = len(bs_entities) + len(bs_dates)
        found_total = found_entities + found_dates
        
        overlap_score = found_total / total_details if total_details > 0 else 0
        
        return {
            'overlap_score': overlap_score,
            'found_count': found_total,
            'total_details': total_details,
            'missing_details': missing_details
        }
    
    def _classify_claim(self, sentence: str) -> str:
        """Classify the type of claim in a sentence."""
        lower = sentence.lower()
        
        # Character trait claims
        if any(word in lower for word in ['was', 'is', 'became', 'turned into']):
            if any(word in lower for word in ['wealthy', 'poor', 'brave', 'kind', 'cruel']):
                return 'character_trait'
            return 'event'
        
        # Motivation claims
        if any(word in lower for word in ['because', 'to', 'in order to', 'motivated']):
            return 'motivation'
        
        # Relationship claims
        if any(word in lower for word in ['mother', 'father', 'brother', 'sister', 'love', 'hate', 'relationship']):
            return 'relationship'
        
        return 'event'
    
    def _assess_importance(self, sentence: str) -> str:
        """Assess the importance of a claim."""
        words = sentence.lower().split()
        
        # High importance keywords (expanded from version 2)
        high_importance = {
            'murdered', 'killed', 'died', 'born', 'father', 'mother', 
            'wealthy', 'poor', 'prison', 'escape'
        }
        if any(word in high_importance for word in words):
            return 'high'
        
        # Medium importance
        if len(sentence.split()) > 15:
            return 'medium'
        
        return 'low'
    
    def _extract_entities(self, sentence: str) -> List[str]:
        """
        Extract key entities (names, places, capitalized concepts).
        Filters out common stop words for better precision.
        """
        entities = []
        words = sentence.split()
        for word in words:
            # Check for capitalization and length, and ensure it's not a stop word
            clean_word = re.sub(r'[^\w]', '', word)
            if (word and word[0].isupper() and 
                len(word) > 2 and 
                clean_word not in self.stop_words):
                entities.append(clean_word)
        return entities

    def _extract_dates(self, sentence: str) -> List[str]:
        """Extract years (e.g., 1852, 1796) from 17th-19th centuries."""
        return re.findall(r'\b(1[789]\d{2})\b', sentence)
    
    def _extract_actions(self, sentence: str) -> List[str]:
        """Extract action verbs from the sentence."""
        # Expanded action words combining both versions
        action_words = {
            'became', 'grew', 'lived', 'died', 'was', 'had', 'made', 'helped',
            'protected', 'raised', 'found', 'discovered', 'traveled', 'moved',
            'worked', 'studied', 'learned', 'taught', 'created', 'built',
            'escaped', 'killed', 'murdered', 'saved', 'rescued'
        }
        
        sentence_lower = sentence.lower()
        found_actions = []
        for action in action_words:
            if action in sentence_lower:
                found_actions.append(action)
        
        return found_actions
    
    def find_semantic_contradictions(
        self,
        backstory_claims: List[Dict],
        evidence_chunks: List[Dict]
    ) -> List[Tuple[str, str, float]]:
        """
        Find semantic contradictions between backstory claims and evidence.
        
        Returns list of (claim, evidence_snippet, confidence) tuples.
        """
        contradictions = []
        
        for claim in backstory_claims:
            claim_text = claim['text'].lower()
            
            for chunk in evidence_chunks:
                chunk_text = chunk['text'].lower()
                similarity = chunk.get('similarity', 0)
                
                # Adjusted threshold from version 2 (0.60 vs 0.65)
                if similarity < 0.60:
                    continue
                
                # Check for antonym pairs
                for antonym1, antonym2 in self.antonym_pairs:
                    if antonym1 in claim_text and antonym2 in chunk_text:
                        # Higher boost from version 2 (0.15 vs 0.10)
                        contradiction_score = min(0.95, similarity + 0.15)
                        contradictions.append((
                            claim['text'],
                            chunk['text'][:100],
                            contradiction_score
                        ))
                        break
        
        return contradictions
    
    def score_evidence_support(
        self,
        backstory_claims: List[Dict],
        evidence_chunks: List[Dict]
    ) -> float:
        """
        Calculate overall support score for backstory claims in evidence.
        
        Returns float between 0 and 1 representing the degree of support.
        """
        if not backstory_claims or not evidence_chunks:
            return 0.5
        
        total_support = 0
        
        for claim in backstory_claims:
            claim_text = claim['text'].lower()
            claim_entities = set(claim.get('entities', []))
            claim_actions = set(claim.get('actions', []))
            
            # Find supporting evidence
            max_support = 0
            
            for chunk in evidence_chunks:
                chunk_text = chunk['text'].lower()
                similarity = chunk.get('similarity', 0)
                
                # Count entity overlap (improved from version 2)
                chunk_words = set(word.lower() for word in chunk_text.split())
                entity_overlap = len({e.lower() for e in claim_entities} & chunk_words)
                
                # Count action overlap
                action_overlap = len(claim_actions & set(chunk_text.split()))
                
                # Combine factors - using higher entity boost from version 2
                entity_boost = entity_overlap * 0.15
                action_boost = action_overlap * 0.15
                
                support_score = min(1.0, similarity + entity_boost + action_boost)
                max_support = max(max_support, support_score)
            
            total_support += max_support
        
        avg_support = total_support / len(backstory_claims)
        return min(1.0, avg_support)
    
    def analyze_causal_consistency(
        self,
        backstory: str,
        evidence_chunks: List[Dict]
    ) -> Dict:
        """
        Analyze if the backstory forms a coherent causal chain with evidence.
        
        Returns dict with:
        - has_causal_chain: Whether evidence shows causal relationships
        - causal_consistency: Float 0-1 indicating consistency
        - backstory_causal_count: Number of causal indicators in backstory
        - evidence_causal_count: Number of causal indicators in evidence
        """
        evidence_text = " ".join([chunk['text'] for chunk in evidence_chunks])
        
        # Count causal indicators in backstory
        backstory_causals = sum(
            1 for indicator in self.causal_indicators
            if indicator in backstory.lower()
        )
        
        # Count causal indicators in evidence
        evidence_causals = sum(
            1 for indicator in self.causal_indicators
            if indicator in evidence_text.lower()
        )
        
        # Assess causal consistency (improved logic from version 2)
        has_causal_chain = evidence_causals > 0
        causal_consistency = 0.8  # Default baseline
        
        if backstory_causals > 0:
            # If backstory relies on causality, we need evidence of it
            if evidence_causals == 0:
                causal_consistency = 0.4
            else:
                # More nuanced scoring from version 2
                causal_consistency = min(1.0, 0.5 + (evidence_causals / (backstory_causals + 1)) * 0.5)
        
        return {
            'has_causal_chain': has_causal_chain,
            'causal_consistency': causal_consistency,
            'backstory_causal_count': backstory_causals,
            'evidence_causal_count': evidence_causals
        }


def enhance_evidence_with_semantic_analysis(
    evidence: List[Dict],
    backstory: str
) -> Tuple[List[Dict], Dict]:
    """
    Enhance evidence chunks with semantic analysis scores.
    
    This function augments the evidence list with additional semantic scores
    that can be used by the judge for better decision making.
    
    Returns:
        Tuple of (enhanced_evidence, analysis_dict) where analysis_dict contains:
        - claims: Extracted backstory claims
        - support_score: Overall support score
        - contradictions: List of contradictions found
        - causal_analysis: Causal consistency analysis
        - detail_check: Detail overlap analysis (anti-hallucination)
    """
    analyzer = SemanticAnalyzer()
    
    # Analyze backstory claims
    claims = analyzer.analyze_backstory_claims(backstory)
    
    # Score evidence support
    support_score = analyzer.score_evidence_support(claims, evidence)
    
    # Find contradictions
    contradictions = analyzer.find_semantic_contradictions(claims, evidence)
    
    # Analyze causal consistency
    causal_analysis = analyzer.analyze_causal_consistency(backstory, evidence)
    
    # Check for specific detail overlap (Hallucination check - from version 2)
    detail_check = analyzer.calculate_detail_overlap(backstory, evidence)
    
    # Add scores to evidence
    for chunk in evidence:
        chunk['semantic_support_score'] = support_score
        chunk['has_contradictions'] = len(contradictions) > 0
        chunk['causal_consistency'] = causal_analysis['causal_consistency']
    
    return evidence, {
        'claims': claims,
        'support_score': support_score,
        'contradictions': contradictions,
        'causal_analysis': causal_analysis,
        'detail_check': detail_check  # Pass this to the judge
    }


if __name__ == "__main__":
    # Test semantic analyzer
    analyzer = SemanticAnalyzer()
    
    test_backstory = "John grew up poor in London in 1852 but became a doctor to help his community."
    claims = analyzer.analyze_backstory_claims(test_backstory)
    
    print("Extracted claims:")
    for claim in claims:
        print(f"  - {claim['text']}")
        print(f"    Type: {claim['type']}, Importance: {claim['importance']}")
        print(f"    Entities: {claim['entities']}, Dates: {claim['dates']}")
        print(f"    Actions: {claim['actions']}")