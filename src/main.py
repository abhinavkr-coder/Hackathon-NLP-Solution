import os
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict
import argparse

from preprocess import NovelPreprocessor, preprocess_backstory
from embeddings import EmbeddingManager, PathwayVectorStore
from retrieve import EvidenceRetriever
from judge import ConsistencyJudge

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NarrativeConsistencySystem:
    def __init__(
        self,
        data_dir: str = "./data",
        results_dir: str = "./results",
        use_llm: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.use_llm = use_llm

        self.results_dir.mkdir(parents=True, exist_ok=True)

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
        novels_dir = self.data_dir / "novels"
        novel_files = list(novels_dir.glob("*.txt"))

        for novel_file in novel_files:
            novel_id = novel_file.stem
            if novel_ids and novel_id not in novel_ids:
                continue

            logger.info(f"Processing novel: {novel_id}")

            chunks = self.preprocessor.preprocess_novel(
                str(novel_file), novel_id
            )
            chunks = self.embedding_manager.create_embeddings(chunks)
            self.vector_store.add_chunks(chunks)

        logger.info("Novel processing complete")

    def load_test_data(self) -> pd.DataFrame:
        test_file = self.data_dir / "test.csv"
        df = pd.read_csv(test_file)
        return df

    def process_single_case(
        self,
        story_id: str,
        novel_id: str,
        backstory: str,
        character_name: str = None
    ) -> Dict:

        logger.info(f"Processing case {story_id} for novel {novel_id}")

        try:
            backstory_clean = preprocess_backstory(backstory)
            retriever = EvidenceRetriever(self.vector_store)

            temporal_evidence = retriever.retrieve_temporal_evidence(
                backstory_clean,
                novel_id,
                top_k=15
            )

            early = temporal_evidence.get("early", [])
            middle = temporal_evidence.get("middle", [])
            late = temporal_evidence.get("late", [])

            logger.info(
                f"Evidence counts — early: {len(early)}, "
                f"middle: {len(middle)}, late: {len(late)}"
            )

            prediction, rationale, confidence = (
                self.judge.judge_with_temporal_constraints(
                    backstory_clean,
                    temporal_evidence,
                    novel_id
                )
            )

            # ✅ ADDED: confidence logging (ONLY change)
            logger.info(
                f"Judgment: {prediction} (confidence: {confidence:.2f})"
            )

            return {
                "story_id": story_id,
                "prediction": prediction,
                "rationale": rationale,
                "confidence": confidence,
                "early_evidence": len(early),
                "middle_evidence": len(middle),
                "late_evidence": len(late),
            }

        except Exception as e:
            logger.error(f"Error processing case {story_id}: {e}")
            return {
                "story_id": story_id,
                "prediction": 0,
                "rationale": f"Error: {str(e)}",
                "confidence": 0.0,
                "early_evidence": 0,
                "middle_evidence": 0,
                "late_evidence": 0,
            }

    def run_evaluation(self) -> pd.DataFrame:
        test_df = self.load_test_data()
        results = []

        for _, row in test_df.iterrows():
            result = self.process_single_case(
                row["story_id"],
                row["novel_id"],
                row["backstory"],
                row.get("character_name")
            )
            results.append(result)

        df = pd.DataFrame(results)
        output_df = df[["story_id", "prediction", "rationale"]]
        output_df.to_csv(self.results_dir / "results.csv", index=False)

        return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--results-dir", default="./results")
    parser.add_argument("--use-llm", action="store_true", default=True)
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    system = NarrativeConsistencySystem(
        data_dir=args.data_dir,
        results_dir=args.results_dir,
        use_llm=args.use_llm and not args.no_llm,
    )

    system.process_novels()
    system.run_evaluation()

    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
