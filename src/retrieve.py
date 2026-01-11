"""
retrieve.py - Intelligent Evidence Retrieval with Character Attribution Safety

This module implements sophisticated retrieval strategies that solve a critical problem
in narrative consistency checking: the "Identity Crisis" problem.

THE IDENTITY CRISIS PROBLEM:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Imagine you're checking if "Thalcave climbed the Andes mountains" is consistent with
a novel. Without proper character filtering, the system might retrieve evidence about
a DIFFERENT character (say, Tom) climbing mountains, and incorrectly mark the backstory
as consistent. This is the "Identity Crisis" - mixing up evidence for different characters.

OUR SOLUTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We use a three-layer defense system:

1. QUERY AUGMENTATION: Prepend character names to all search queries
   Before: "climbed the mountains"
   After: "Thalcave climbed the mountains"
   
2. EXPANDED SEARCH: Retrieve 3x more candidates than needed, knowing we'll filter many
   
3. STRICT FILTERING: Only keep chunks that explicitly mention the character
   with fallback to prevent over-filtering

Think of this like a legal investigation where we need evidence specifically about
the defendant, not just evidence about similar cases involving other people.
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from embeddings import PathwayVectorStore, EmbeddingManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """
    Retrieves relevant evidence from novels using multiple sophisticated strategies.
    
    The core insight is that different types of backstory claims require different
    retrieval approaches. A claim about childhood trauma needs different evidence
    than a claim about a character's profession. We provide multiple retrieval
    methods that can be combined for comprehensive evidence gathering.
    """
    
    def __init__(self, vector_store: PathwayVectorStore):
        """
        Initialize the retriever with a vector store.
        
        Args:
            vector_store: A PathwayVectorStore containing embedded novel chunks
        """
        self.vector_store = vector_store
    
    def decompose_backstory(self, backstory: str) -> List[str]:
        """
        Break a backstory into atomic claims that can be individually verified.
        
        This is a crucial step because complex backstories contain multiple verifiable
        claims that each need separate evidence. For example:
        
        "John grew up poor in London and became a doctor to help his community"
        
        Contains these atomic claims:
        1. "John grew up poor" (economic status claim)
        2. "grew up in London" (location claim)
        3. "became a doctor" (profession claim)
        4. "to help his community" (motivation claim)
        
        Each claim requires different types of supporting evidence from the novel.
        By decomposing the backstory, we can search for each type of evidence
        separately and then aggregate the results.
        
        Args:
            backstory: The complete backstory string to decompose
            
        Returns:
            List of claim strings, including individual claims plus the full backstory
        """
        # We split on punctuation and coordinating conjunctions that typically
        # separate independent claims. The pattern captures:
        # - Periods and semicolons (sentence boundaries)
        # - "and", "but", "yet" (conjunctions joining separate claims)
        potential_claims = re.split(r'[.;]|\band\b|\bbut\b|\byet\b', backstory)
        
        # Clean up the claims by stripping whitespace and filtering out
        # very short fragments that are unlikely to be meaningful claims
        claims = [
            claim.strip()
            for claim in potential_claims
            if claim.strip() and len(claim.strip().split()) > 3
        ]
        
        # Always include the full backstory as a holistic claim because
        # sometimes the combination of claims creates meaning that individual
        # claims don't capture
        claims.append(backstory)
        
        logger.info(f"Decomposed backstory into {len(claims)} atomic claims")
        return claims
    
    def retrieve_for_backstory(
        self,
        backstory: str,
        novel_id: str,
        top_k: int = 15
    ) -> List[Dict]:
        """
        Retrieve evidence relevant to an entire backstory using multi-query search.
        
        This is the basic retrieval method that doesn't assume we know the character
        name. It works by breaking down the backstory into claims and searching for
        evidence supporting each claim independently, then aggregating the results.
        
        The multi-query approach is important because it ensures we find evidence
        for ALL parts of the backstory, not just the parts that happen to match
        best with a single query.
        
        Args:
            backstory: The character backstory to find evidence for
            novel_id: Which novel to search within
            top_k: How many evidence chunks to return
            
        Returns:
            List of evidence chunks, each containing text and similarity score
        """
        logger.info(f"Retrieving evidence for novel {novel_id}")
        
        # First, break the backstory into atomic claims
        claims = self.decompose_backstory(backstory)
        logger.info(f"Extracted {len(claims)} claims from backstory")
        
        # Search for each claim independently. We allocate chunks proportionally:
        # if we want 15 total chunks and have 5 claims, we get ~3 chunks per claim
        # The max(3, ...) ensures we get at least 3 chunks per claim
        all_chunks = self.vector_store.multi_query_search(
            queries=claims,
            novel_id=novel_id,
            top_k_per_query=max(3, top_k // len(claims))
        )
        
        # Score the evidence quality and take the top-k best chunks
        # This re-ranking step is important because multi_query_search returns
        # chunks in the order they were retrieved, not necessarily in quality order
        scored_chunks = self._score_evidence_quality(all_chunks, backstory)
        evidence = scored_chunks[:top_k]
        
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
        Retrieve evidence with STRICT character filtering to prevent Identity Crisis.
        
        This is our most important retrieval method because it solves the fundamental
        problem of character attribution. Without this, we might use evidence about
        Character A to judge a backstory about Character B.
        
        THE STRATEGY:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        1. QUERY AUGMENTATION
        We don't just search for "climbed mountains" - we search for "Thalcave 
        climbed mountains". This biases the embedding space toward passages that
        actually mention the character.
        
        2. EXPANDED SEARCH
        We retrieve 3x more chunks than we need because we expect to filter out
        many chunks that don't mention the character. This prevents us from ending
        up with too few evidence chunks after filtering.
        
        3. STRICT FILTERING
        We only keep chunks that explicitly mention the character name (or a 
        significant part of it for multi-word names). This is strict but necessary
        to prevent misattribution.
        
        4. FALLBACK MECHANISM
        If strict filtering leaves us with too few chunks (less than 3), we relax
        the filtering to include the best semantic matches. This handles cases where
        pronouns are used extensively.
        
        Args:
            backstory: The character backstory to verify
            character_name: The specific character this backstory is about
            novel_id: Which novel to search
            top_k: Target number of evidence chunks to return
            
        Returns:
            List of evidence chunks that specifically mention the character
        """
        logger.info(f"Retrieving character-focused evidence for '{character_name}' in {novel_id}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 1: Query Augmentation
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # We decompose the backstory and prepend the character name to each claim
        # This creates queries like "Thalcave grew up poor" instead of just
        # "grew up poor", which would match any character with that background
        raw_claims = self.decompose_backstory(backstory)
        
        augmented_queries = [
            f"{character_name} {claim}" 
            for claim in raw_claims
        ]
        
        logger.info(f"Created {len(augmented_queries)} character-augmented queries")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 2: Expanded Search
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # We ask for 3x more candidates because we expect to filter out many
        # The max(5, ...) ensures we get at least 5 candidates per query
        all_chunks = self.vector_store.multi_query_search(
            queries=augmented_queries,
            novel_id=novel_id,
            top_k_per_query=max(5, (top_k * 3) // len(augmented_queries))
        )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 3: Deduplication
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Multiple queries might return the same chunk, so we deduplicate based
        # on chunk_id to avoid processing the same text multiple times
        seen_ids = set()
        unique_chunks = []
        
        for chunk in all_chunks:
            if chunk['chunk_id'] not in seen_ids:
                unique_chunks.append(chunk)
                seen_ids.add(chunk['chunk_id'])
        
        logger.info(f"After deduplication: {len(unique_chunks)} unique chunks")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 4: Strict Character Filtering
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # This is where we enforce that chunks MUST mention the character
        filtered_chunks = self._filter_by_character_mention(
            unique_chunks, character_name
        )
        
        logger.info(
            f"Character filtering: {len(unique_chunks)} → {len(filtered_chunks)} chunks "
            f"(kept {len(filtered_chunks)/max(len(unique_chunks), 1)*100:.1f}%)"
        )
        
        # If strict filtering leaves very few chunks, do NOT add back
        # semantically-similar but character-unattributed chunks. This avoids
        # the Identity Crisis where evidence for other characters is used.
        if len(filtered_chunks) < 3:
            logger.warning(
                "Strict filtering left too few chunks. Returning strictly filtered chunks (no fallback)."
            )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 6: Quality Scoring and Final Selection
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Score the remaining chunks for quality and return the best ones
        scored_chunks = self._score_evidence_quality(filtered_chunks, backstory)
        final_evidence = scored_chunks[:top_k]
        
        logger.info(f"Returning {len(final_evidence)} character-specific evidence chunks")
        return final_evidence
    
    def _filter_by_character_mention(
        self,
        chunks: List[Dict],
        character_name: str
    ) -> List[Dict]:
        """
        Filter chunks to only those that explicitly mention the character.
        
        This implements the strict filtering that prevents Identity Crisis. We use
        a sophisticated matching strategy that handles multi-word names properly.
        
        For example, with "Tom Ayrton":
        - We split into tokens: ["tom", "ayrton"]
        - We ignore short words like "Mr", "Dr" that aren't distinctive
        - We match if the full name appears OR if significant parts appear
        
        This balances strictness (preventing misattribution) with flexibility
        (handling name variations like "Tom" vs "Tom Ayrton").
        
        Args:
            chunks: List of candidate evidence chunks
            character_name: The character name to filter for
            
        Returns:
            List of chunks that mention the character
        """
        filtered_chunks = []
        
        # Prepare name tokens for matching
        # We split multi-word names and filter out short titles that aren't
        # distinctive enough (like "Mr", "Dr", "de", "von")
        name_tokens = [
            token.lower() 
            for token in character_name.split() 
            if len(token) > 2  # Ignore short titles/particles
        ]
        
        # If all tokens were filtered out (rare), use the full name
        if not name_tokens:
            name_tokens = [character_name.lower()]
        
        logger.debug(f"Character matching using tokens: {name_tokens}")
        
        # Check each chunk for character mention
        for chunk in chunks:
            text_lower = chunk['text'].lower()
            match_found = False
            
            # Strategy 1: Try to match the full name first (most reliable)
            if character_name.lower() in text_lower:
                match_found = True
                chunk['match_type'] = 'full_name'
            else:
                # Strategy 2: Match if any significant name part appears
                # For multi-word names, this handles cases where only part
                # of the name is used (like "Watson" instead of "John Watson")
                for token in name_tokens:
                    if token in text_lower:
                        match_found = True
                        chunk['match_type'] = f'partial_{token}'
                        break
            
            if match_found:
                filtered_chunks.append(chunk)
        
        return filtered_chunks
    
    def _score_evidence_quality(
        self,
        chunks: List[Dict],
        backstory: str
    ) -> List[Dict]:
        """
        Score and re-rank evidence based on multiple quality metrics.
        
        Semantic similarity alone isn't enough to determine the best evidence.
        We also want chunks that:
        - Have strong topical overlap with the backstory (word overlap)
        - Are substantive and informative (length)
        - Are directly relevant (not just tangentially related)
        
        This quality scoring helps us prioritize the most useful evidence for
        the consistency judge to evaluate.
        
        Quality Score Calculation:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        Base Score: Semantic similarity from embeddings (0-1)
        + Topical Overlap Boost: 0-0.15 based on shared words
        + Length Boost: +0.05 for substantive chunks (>30 words)
        = Final Quality Score (normalized to 0-1)
        
        Args:
            chunks: List of evidence chunks to score
            backstory: The backstory for calculating topical relevance
            
        Returns:
            Chunks sorted by quality score (highest first)
        """
        # Extract meaningful words from the backstory for overlap calculation
        # We filter out very short words (≤3 chars) to focus on content words
        backstory_words = set(
            word.lower() 
            for word in backstory.split() 
            if len(word) > 3
        )
        
        for chunk in chunks:
            # Start with the semantic similarity as the base score
            quality_score = chunk['similarity']
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Factor 1: Topical Relevance (word overlap)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Chunks that share many content words with the backstory are
            # more likely to be topically relevant, even if the semantic
            # similarity score doesn't capture it perfectly
            chunk_words = set(
                word.lower() 
                for word in chunk['text'].split() 
                if len(word) > 3
            )
            
            # Calculate what fraction of backstory words appear in the chunk
            overlap_ratio = len(backstory_words & chunk_words) / max(len(backstory_words), 1)
            quality_score += overlap_ratio * 0.15
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Factor 2: Content Density (chunk length)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Longer chunks tend to provide more context and are more likely
            # to contain the kind of nuanced evidence we need for consistency
            # checking. We give a small boost to substantive chunks.
            chunk_length = len(chunk['text'].split())
            if chunk_length > 30:
                quality_score += 0.05
            
            # Normalize to ensure the score stays in the [0, 1] range
            chunk['quality_score'] = min(1.0, quality_score)
        
        # Re-sort by quality score (highest first)
        chunks.sort(key=lambda x: x['quality_score'], reverse=True)
        
        return chunks
    
    def retrieve_temporal_evidence(
        self,
        backstory: str,
        novel_id: str,
        top_k: int = 15
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve evidence organized by narrative position (early, middle, late).
        
        This method is crucial for understanding narrative development and checking
        consistency over time. Events early in a novel establish constraints that
        must hold later. Character development should be consistent with their
        backstory throughout the narrative arc.
        
        Why this matters:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        If a backstory claims "John overcame his fear of heights", we should see:
        - Early evidence: John being afraid of heights
        - Middle evidence: John confronting this fear
        - Late evidence: John confident at heights
        
        Without temporal organization, we might miss this developmental arc.
        
        Args:
            backstory: The backstory to find evidence for
            novel_id: Which novel to search
            top_k: Total evidence chunks to return (distributed across periods)
            
        Returns:
            Dictionary with keys 'early', 'middle', 'late', each containing
            evidence chunks from that narrative period
        """
        logger.info(f"Retrieving temporally-organized evidence for {novel_id}")
        
        # First, get a larger pool of evidence using standard retrieval
        # We retrieve 2x what we need to ensure good coverage across all periods
        all_evidence = self.retrieve_for_backstory(backstory, novel_id, top_k * 2)
        
        # Calculate the maximum chunk ID for this novel to determine position
        # Chunk IDs are sequential, so we can use them to determine position
        # in the narrative (assuming chunks are created in reading order)
        max_chunk_id = max(
            chunk['chunk_id']
            for chunk in self.vector_store.chunks
            if chunk['novel_id'] == novel_id
        )
        
        # Initialize our temporal buckets
        temporal_evidence = {
            'early': [],    # First third of the novel
            'middle': [],   # Middle third
            'late': []      # Final third
        }
        
        # Categorize each chunk by its position in the novel
        for chunk in all_evidence:
            # Calculate relative position (0 = start, 1 = end)
            position = chunk['chunk_id'] / max_chunk_id
            
            # Assign to the appropriate temporal bucket
            if position < 0.33:
                temporal_evidence['early'].append(chunk)
            elif position < 0.66:
                temporal_evidence['middle'].append(chunk)
            else:
                temporal_evidence['late'].append(chunk)
        
        # Ensure balanced representation across periods
        # We want roughly equal evidence from each period to avoid bias
        chunks_per_period = top_k // 3
        for period in temporal_evidence:
            temporal_evidence[period] = temporal_evidence[period][:chunks_per_period]
        
        logger.info(
            f"Temporal distribution: {len(temporal_evidence['early'])} early, "
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
        Retrieve evidence that shows causal relationships and narrative constraints.
        
        This addresses one of the deepest challenges in consistency checking: finding
        passages that reveal not just what happened, but WHY it happened and what it
        prevented from happening.
        
        For example, if a backstory claims "John became a doctor because his sister
        died from lack of medical care", we need to find evidence that:
        1. Mentions the sister's death (the cause)
        2. Shows this motivated John (the causal link)
        3. Explains his choice of profession (the effect)
        
        Passages with causal language are much more valuable for this than simple
        descriptive passages, so we boost their scores significantly.
        
        Causal indicators we look for:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        - Explicit causation: "because", "therefore", "as a result"
        - Motivation: "motivated", "driven by", "compelled"
        - Constraints: "couldn't", "impossible", "prevented"
        - Obligation: "had to", "must", "required"
        
        Args:
            backstory: The backstory containing causal claims
            novel_id: Which novel to search
            top_k: Number of evidence chunks to return
            
        Returns:
            Evidence chunks ranked by causal relevance
        """
        logger.info(f"Retrieving causal evidence for {novel_id}")
        
        # Get a larger pool of candidate evidence
        evidence = self.retrieve_for_backstory(backstory, novel_id, top_k * 2)
        
        # Define causal indicators that signal important relationships
        causal_indicators = [
            'because', 'therefore', 'thus', 'consequently', 'as a result',
            'due to', 'caused by', 'led to', 'resulted in',
            'motivated', 'driven by', 'compelled', 'forced',
            'couldn\'t', 'impossible', 'prevented', 'forbade',
            'had to', 'must', 'required', 'necessary'
        ]
        
        # Score each chunk based on causal language
        for chunk in evidence:
            text_lower = chunk['text'].lower()
            
            # Count how many causal indicators appear in this chunk
            # More indicators suggest more explicit causal reasoning
            causal_score = sum(
                1 for indicator in causal_indicators
                if indicator in text_lower
            )
            
            # Boost the similarity score based on causal language
            # Each indicator adds 15% to the score, which can significantly
            # promote chunks with rich causal content
            chunk['causal_boosted_similarity'] = (
                chunk['similarity'] * (1 + 0.15 * causal_score)
            )
            
            # Store the count for potential debugging
            chunk['causal_indicator_count'] = causal_score
        
        # Re-sort by causal-boosted similarity
        evidence.sort(key=lambda x: x['causal_boosted_similarity'], reverse=True)
        
        logger.info(
            f"Top chunk has {evidence[0]['causal_indicator_count']} causal indicators"
            if evidence else "No evidence found"
        )
        
        return evidence[:top_k]
    
    def retrieve_hybrid(
        self,
        backstory: str,
        character_name: Optional[str],
        novel_id: str,
        top_k: int = 15,
        use_character_filter: bool = True,
        use_causal_boost: bool = True
    ) -> List[Dict]:
        """
        Hybrid retrieval combining multiple strategies for maximum effectiveness.
        
        This is the most comprehensive retrieval method, combining:
        - Character-focused filtering (if character name provided)
        - Causal language boosting
        - Quality scoring
        
        Use this when you want the best possible evidence retrieval and can
        afford the computational cost of multiple scoring passes.
        
        Args:
            backstory: The backstory to find evidence for
            character_name: Optional character name for focused retrieval
            novel_id: Which novel to search
            top_k: Number of evidence chunks to return
            use_character_filter: Whether to apply strict character filtering
            use_causal_boost: Whether to boost causal language
            
        Returns:
            Comprehensively scored and filtered evidence chunks
        """
        logger.info(f"Hybrid retrieval for {novel_id} (character: {character_name or 'None'})")
        
        # Step 1: Get base evidence using appropriate method
        if character_name and use_character_filter:
            evidence = self.retrieve_with_character_focus(
                backstory, character_name, novel_id, top_k * 2
            )
        else:
            evidence = self.retrieve_for_backstory(backstory, novel_id, top_k * 2)
        
        # Step 2: Apply causal boosting if requested
        if use_causal_boost:
            causal_indicators = [
                'because', 'therefore', 'thus', 'consequently', 'as a result',
                'due to', 'caused by', 'led to', 'resulted in',
                'motivated', 'driven by', 'compelled', 'forced',
                'couldn\'t', 'impossible', 'prevented', 'forbade',
                'had to', 'must', 'required', 'necessary'
            ]
            
            for chunk in evidence:
                text_lower = chunk['text'].lower()
                causal_score = sum(
                    1 for indicator in causal_indicators
                    if indicator in text_lower
                )
                chunk['causal_score'] = causal_score
        
        # Step 3: Final quality scoring (incorporates all factors)
        evidence = self._score_evidence_quality(evidence, backstory)
        
        # Step 4: Return top-k
        return evidence[:top_k]


class ConstraintExtractor:
    """
    Extracts narrative constraints from retrieved evidence.
    
    This class moves us from "here's relevant text" to "here's what this text
    tells us MUST be true about the backstory". It's the bridge between evidence
    retrieval and consistency judgment.
    """
    
    @staticmethod
    def extract_character_constraints(
        evidence: List[Dict],
        character_name: str
    ) -> List[Dict]:
        """
        Extract hard constraints about a character from evidence.
        
        These are statements that directly describe the character and establish
        facts that any consistent backstory must respect.
        
        Args:
            evidence: List of evidence chunks
            character_name: The character to extract constraints for
            
        Returns:
            List of constraint dictionaries containing text, similarity, and type
        """
        constraints = []
        
        for chunk in evidence:
            text = chunk['text']
            
            # If this chunk mentions the character, it potentially establishes
            # constraints about them
            if character_name.lower() in text.lower():
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
        
        This is a heuristic approach that flags passages for closer inspection.
        A production system would use a Natural Language Inference (NLI) model
        for more sophisticated contradiction detection.
        
        Our heuristic: High similarity + negation words = potential contradiction
        The reasoning is that if a passage is semantically similar to a claim
        but contains negation, it might be saying the opposite of what the
        claim states.
        
        Args:
            evidence: Retrieved evidence chunks
            backstory_claims: Individual claims from the backstory
            
        Returns:
            List of (evidence_text, claim, confidence) tuples for potential
            contradictions
        """
        potential_contradictions = []
        
        # Words that often signal negation or contradiction
        negation_words = ['not', 'never', 'no', 'none', 'nobody', 'nothing']
        
        for chunk in evidence:
            text_lower = chunk['text'].lower()
            has_negation = any(word in text_lower for word in negation_words)
            
            for claim in backstory_claims:
                # If a chunk is highly similar to a claim but contains negation,
                # it might be contradicting the claim
                # Example: Claim "John was wealthy" vs Evidence "John was not wealthy"
                if chunk['similarity'] > 0.7 and has_negation:
                    potential_contradictions.append((
                        chunk['text'],
                        claim,
                        chunk['similarity']
                    ))
        
        return potential_contradictions


if __name__ == "__main__":
    print("━" * 70)
    print("Evidence Retrieval Module - Loaded Successfully")
    print("━" * 70)
    print("\nThis module provides sophisticated evidence retrieval strategies:")
    print("  • retrieve_for_backstory() - Basic multi-query retrieval")
    print("  • retrieve_with_character_focus() - Strict character filtering")
    print("  • retrieve_temporal_evidence() - Narrative arc analysis")
    print("  • retrieve_causal_chain() - Causal relationship detection")
    print("  • retrieve_hybrid() - Combined strategies for best results")
    print("\nUse main.py to run the full consistency checking pipeline.")
    print("━" * 70)