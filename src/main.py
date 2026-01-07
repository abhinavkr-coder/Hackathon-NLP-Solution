"""
main.py - Complete Pipeline Orchestration

This is the main entry point that ties everything together. It orchestrates
the entire workflow from raw data to final predictions.

The pipeline follows this flow:
1. Load and preprocess novels (turning raw text into searchable chunks)
2. Create embeddings (representing chunks as semantic vectors)
3. Load backstories and test cases
4. For each test case:
   - Retrieve relevant evidence from the novel
   - Judge consistency based on evidence
5. Write results to CSV

Think of this as the conductor of an orchestra - it doesn't play any instruments
itself, but it coordinates all the components to create a cohesive performance.
"""

import os
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict
import argparse

# Import our custom modules
from preprocess import NovelPreprocessor, preprocess_backstory
from embeddings import EmbeddingManager, PathwayVectorStore
from retrieve import EvidenceRetriever
from judge import ConsistencyJudge

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NarrativeConsistencySystem:
    """
    Complete system for evaluating backstory consistency in novels.
    
    This class encapsulates the entire pipeline, making it easy to:
    - Process multiple novels
    - Handle batches of test cases
    - Save and load intermediate results (for resuming long runs)
    - Configure different strategies (heuristic vs LLM-based judgment)
    """
    
    def __init__(
        self,
        data_dir: str = "./data",
        results_dir: str = "./results",
        use_llm: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize the system with configuration parameters.
        
        Args:
            data_dir: Directory containing novels/, backstories.csv, test.csv
            results_dir: Directory where results will be saved
            use_llm: Whether to use LLM for judgment (vs rule-based heuristics)
            chunk_size: Size of text chunks in words
            chunk_overlap: Overlap between chunks in words
        """
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.use_llm = use_llm
        
        # Create results directory if it doesn't exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        logger.info("Initializing system components...")
        self.preprocessor = NovelPreprocessor(
            chunk_size=chunk_size,
            overlap=chunk_overlap
        )
        self.embedding_manager = EmbeddingManager()
        self.vector_store = PathwayVectorStore(self.embedding_manager)
        self.judge = ConsistencyJudge(use_llm=use_llm)
        
        logger.info("System initialized successfully")
    
    def process_novels(self, novel_ids: List[str] = None):
        """
        Process all novels: preprocess, embed, and index for retrieval.
        
        This is the most time-consuming step, especially for 100k+ word novels.
        For production, you'd want to cache these embeddings to disk so you
        don't have to recompute them every time.
        
        Args:
            novel_ids: List of specific novel IDs to process. If None, processes all.
        """
        novels_dir = self.data_dir / "novels"
        
        if not novels_dir.exists():
            raise FileNotFoundError(f"Novels directory not found: {novels_dir}")
        
        # Find all novel files
        novel_files = list(novels_dir.glob("*.txt"))
        
        if not novel_files:
            raise FileNotFoundError(f"No .txt files found in {novels_dir}")
        
        logger.info(f"Found {len(novel_files)} novel files")
        
        # Process each novel
        for novel_file in novel_files:
            # Extract novel ID from filename (e.g., "novel_1.txt" -> "novel_1")
            novel_id = novel_file.stem
            
            # Skip if not in requested IDs
            if novel_ids and novel_id not in novel_ids:
                continue
            
            logger.info(f"Processing novel: {novel_id}")
            
            try:
                # Step 1: Preprocess (chunk the novel)
                chunks = self.preprocessor.preprocess_novel(
                    str(novel_file),
                    novel_id
                )
                logger.info(f"  Created {len(chunks)} chunks")
                
                # Step 2: Generate embeddings
                chunks_with_embeddings = self.embedding_manager.create_embeddings(chunks)
                logger.info(f"  Generated embeddings")
                
                # Step 3: Add to vector store
                self.vector_store.add_chunks(chunks_with_embeddings)
                logger.info(f"  Added to vector store")
                
            except Exception as e:
                logger.error(f"Error processing {novel_id}: {e}")
                continue
        
        logger.info("Novel processing complete")
    
    def load_test_data(self) -> pd.DataFrame:
        """
        Load test cases (backstories and their corresponding novels).
        
        Expected format of test.csv:
        - story_id: Unique identifier for each test case
        - novel_id: Which novel to check against
        - character_name: (optional) Name of the character
        - backstory: The hypothetical backstory text
        """
        test_file = self.data_dir / "test.csv"
        
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")
        
        df = pd.read_csv(test_file)
        logger.info(f"Loaded {len(df)} test cases")
        
        # Validate required columns
        required_cols = ['story_id', 'novel_id', 'backstory']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Test file missing required columns: {missing_cols}")
        
        return df
    
    def process_single_case(
        self,
        story_id: str,
        novel_id: str,
        backstory: str,
        character_name: str = None
    ) -> Dict:
        """
        Process a single test case: retrieve evidence and judge consistency.
        
        This is where all the components come together:
        1. Retrieval finds relevant passages
        2. Judge evaluates consistency based on evidence
        3. We package the results for output
        """
        logger.info(f"Processing case {story_id} for novel {novel_id}")
        
        try:
            # Step 1: Clean backstory
            backstory_clean = preprocess_backstory(backstory)
            
            # Step 2: Retrieve evidence
            retriever = EvidenceRetriever(self.vector_store)
            
            if character_name:
                evidence = retriever.retrieve_with_character_focus(
                    backstory_clean,
                    character_name,
                    novel_id,
                    top_k=15
                )
            else:
                evidence = retriever.retrieve_for_backstory(
                    backstory_clean,
                    novel_id,
                    top_k=15
                )
            
            logger.info(f"  Retrieved {len(evidence)} evidence chunks")
            
            # Step 3: Judge consistency
            prediction, rationale, confidence = self.judge.judge_consistency(
                backstory_clean,
                evidence,
                novel_id
            )
            
            logger.info(f"  Judgment: {prediction} (confidence: {confidence:.2f})")
            
            return {
                'story_id': story_id,
                'prediction': prediction,
                'rationale': rationale,
                'confidence': confidence,
                'evidence_count': len(evidence)
            }
            
        except Exception as e:
            logger.error(f"Error processing case {story_id}: {e}")
            # Return a default "uncertain" result
            return {
                'story_id': story_id,
                'prediction': 0,
                'rationale': f"Error during processing: {str(e)}",
                'confidence': 0.0,
                'evidence_count': 0
            }
    
    def run_evaluation(self, save_intermediate: bool = True) -> pd.DataFrame:
        """
        Run the complete evaluation pipeline on all test cases.
        
        This is the main method that produces the final results.csv file.
        
        Args:
            save_intermediate: Whether to save results after each case
                             (useful for long runs that might be interrupted)
        
        Returns:
            DataFrame with results for all test cases
        """
        logger.info("Starting evaluation pipeline")
        
        # Load test data
        test_df = self.load_test_data()
        
        # Process each test case
        results = []
        
        for idx, row in test_df.iterrows():
            story_id = row['story_id']
            novel_id = row['novel_id']
            backstory = row['backstory']
            character_name = row.get('character_name', None)
            
            logger.info(f"\nProcessing {idx + 1}/{len(test_df)}: {story_id}")
            
            result = self.process_single_case(
                story_id,
                novel_id,
                backstory,
                character_name
            )
            
            results.append(result)
            
            # Save intermediate results
            if save_intermediate and (idx + 1) % 5 == 0:
                self._save_results(results, suffix="_intermediate")
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Save final results
        self._save_results(results)
        
        logger.info("\nEvaluation complete!")
        return results_df
    
    def _save_results(self, results: List[Dict], suffix: str = ""):
        """
        Save results to CSV in the required format.
        
        The output format matches the competition requirements:
        - story_id: Identifier
        - prediction: 1 (consistent) or 0 (inconsistent)
        - rationale: Explanation (optional but encouraged)
        """
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Ensure correct column order
        output_df = df[['story_id', 'prediction', 'rationale']]
        
        # Save to CSV
        output_file = self.results_dir / f"results{suffix}.csv"
        output_df.to_csv(output_file, index=False)
        
        logger.info(f"Results saved to {output_file}")


def main():
    """
    Main entry point with command-line argument parsing.
    
    This allows users to configure the system from the command line:
    python main.py --use-llm --data-dir ./data --results-dir ./results
    """
    parser = argparse.ArgumentParser(
        description="Evaluate backstory consistency in narrative texts"
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='./data',
        help='Directory containing novels, backstories, and test data'
    )
    
    parser.add_argument(
        '--results-dir',
        type=str,
        default='./results',
        help='Directory where results will be saved'
    )
    
    parser.add_argument(
        '--use-llm',
        action='store_true',
        default=True,
        help='Use LLM for judgment (default: True)'
    )
    
    parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Use heuristic judgment instead of LLM'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Size of text chunks in words (default: 1000)'
    )
    
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=200,
        help='Overlap between chunks in words (default: 200)'
    )
    
    args = parser.parse_args()
    
    # Handle LLM flag
    use_llm = args.use_llm and not args.no_llm
    
    logger.info("="*60)
    logger.info("NARRATIVE CONSISTENCY EVALUATION SYSTEM")
    logger.info("="*60)
    logger.info(f"Configuration:")
    logger.info(f"  Data directory: {args.data_dir}")
    logger.info(f"  Results directory: {args.results_dir}")
    logger.info(f"  Judgment method: {'LLM-based' if use_llm else 'Heuristic'}")
    logger.info(f"  Chunk size: {args.chunk_size} words")
    logger.info(f"  Chunk overlap: {args.chunk_overlap} words")
    logger.info("="*60)
    
    # Initialize system
    system = NarrativeConsistencySystem(
        data_dir=args.data_dir,
        results_dir=args.results_dir,
        use_llm=use_llm,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    # Process novels
    logger.info("\nStep 1: Processing novels...")
    system.process_novels()
    
    # Run evaluation
    logger.info("\nStep 2: Evaluating test cases...")
    results_df = system.run_evaluation()
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("EVALUATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total test cases: {len(results_df)}")
    logger.info(f"Consistent predictions: {(results_df['prediction'] == 1).sum()}")
    logger.info(f"Inconsistent predictions: {(results_df['prediction'] == 0).sum()}")
    if 'confidence' in results_df.columns:
        logger.info(f"Average confidence: {results_df['confidence'].mean():.3f}")
    logger.info("="*60)
    
    logger.info("\nResults saved to: " + str(system.results_dir / "results.csv"))
    logger.info("\nPipeline complete!")


if __name__ == "__main__":
    main()