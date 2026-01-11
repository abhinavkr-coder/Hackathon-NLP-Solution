Narrative Consistency Evaluation System
Kharagpur Data Science Hackathon 2026 - Track A Solution
This system is designed to solve the "Global Consistency" problem in long-form narratives. unlike standard RAG pipelines that optimize for plausibility, this architecture optimizes for verifiability, constraint tracking, and hallucination resistance.

🚀 Key Differentiators: Why This Isn't Just RAG
Standard RAG pipelines often fail on this task because they confuse "topical similarity" with "factual support". Our system implements specific mechanisms to counter this:

1. "Zombie Story" Detection (Anti-Hallucination)
The Problem: LLMs often hallucinate consistency because a backstory sounds like the character (e.g., "The pirate captain fought a duel").

Our Solution: The SemanticAnalyzer calculates a Keyword Support Score alongside vector similarity. If specific actions (verbs) or objects (nouns) in the backstory lack direct keyword evidence in the retrieved text, the system flags it as a "Zombie Story" (high hallucination risk) and forces a rejection, even if the vector score is high.

2. Strict Character-Focused Retrieval
The Problem: Backstories often claim generic actions ("He climbed a mountain") that match other characters' scenes, leading to False Positives (Identity Crisis).

Our Solution: The EvidenceRetriever uses Query Augmentation (prepending character names to claims) and Strict Name Filtering. It discards evidence chunks that do not explicitly mention the target character, preventing cross-character contamination.

3. Atomic Claim Decomposition
The Problem: A paragraph-long backstory is too complex for a single vector search.

Our Solution: We decompose backstories into atomic claims (e.g., "Born in 1852", "Lost a finger"). Each claim is verified independently. If any critical claim is unsupported, the entire backstory is marked inconsistent.

4. Fine-Tuned Embedding Model
The Problem: Off-the-shelf models struggle to distinguish between consistent character history and plausible but false fan-fiction.

Our Solution: We fine-tuned all-MiniLM-L6-v2 on a custom dataset (train.csv) using Contrastive Loss. This pushes the vector space to separate true narrative events from fabricated ones, specifically for narrative contexts.

🛠️ Installation & Setup
Clone the repository:

Bash

git clone <repo_url>
cd <repo_name>
Install dependencies:

Bash

pip install -r requirements.txt
Note: This project relies on pathway for vector storage and sentence-transformers for embeddings.

Configure API Key (Optional but Recommended): Create a .env file in the root directory:

Code snippet

CEREBRAS_API_KEY=your_key_here
If no key is provided, the system falls back to a robust Heuristic Judge.

🏃‍♂️ How to Run
1. Full Evaluation Pipeline
Run the main script to process novels, generate embeddings, and evaluate all test cases in data/test.csv.

Bash

python src/main.py --chunk-size 500 --chunk-overlap 100
Arguments:

--use-llm: Enable Llama-3.1 reasoning (default).

--no-llm: Force heuristic/rule-based mode.

--chunk-size: Word count per chunk (optimized at 500 for narrative precision).

2. Manual Model Training (Fine-Tuning)
If you want to re-train the embedding model on new data:

Bash

python src/train_embeddings.py
This script reads train.csv, applies CosineSimilarityLoss, and saves the optimized model to ./fine_tuned_model.

📂 Project Structure
src/main.py: Pipeline conductor. Orchestrates loading, retrieval, and judgment.

src/judge.py: The decision engine. Contains the logic for Hallucination Risk calculation and Safety Overrides.

src/retrieve.py: Implements "Decomposition" and "Character-Focused" retrieval strategies.

src/semantic_analyzer.py: Performs linguistic checks (entity verification, antonym detection, keyword support).

src/train_embeddings.py: Script for fine-tuning the sentence transformer.

src/embeddings.py: Pathway vector store integration.


“The core task is a decision problem: determining whether a hypothesized past can causally and logically produce an observed future.” — Hackathon Guidelines