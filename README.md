# Narrative Consistency Evaluation System

### Kharagpur Data Science Hackathon 2026 - Track A Submission

This system acts as a digital detective. It does not simply match keywords; it evaluates whether a hypothetical character backstory is **causally and logically consistent** with the constraints of a 100,000+ word novel.

It uses **Pathway** for data ingestion/retrieval and offers a hybrid judgment engine (LLM + Heuristic).

## 🚀 What Makes This Code Special?

Unlike standard RAG pipelines, this solution implements specialized logic for narrative analysis:

1. **Fine-Tuned Embeddings (`train_embeddings.py`)**
* The system includes a training module to fine-tune `all-MiniLM-L6-v2`.
* It learns to associate specific characters with their *canonical* events and dissociate them from contradictory "false" events using Contrastive Loss.


2. **Intelligent "Detective" Retrieval (`retrieve.py`)**
* **Claim Decomposition:** Breaks complex backstories into atomic claims (e.g., "Born in London" vs. "Became a Doctor") to verify them independently.
* **Temporal Evidence:** Categorizes evidence into Early, Middle, and Late novel segments to ensure consistency across the narrative arc.
* **Causal Chain Boosting:** Prioritizes passages containing causal language ("because", "therefore", "led to") to understand narrative constraints.


3. **Hybrid Judgment Engine (`judge.py`)**
* **Heuristic Mode:** Performs fast antonym checking (e.g., Backstory: "Wealthy" vs. Novel: "Poverty") and negation detection.
* **LLM Mode (Cerebras):** Uses Llama 3.1-8B to perform deep reasoning on the retrieved evidence, specifically looking for causal contradictions.



## 📂 Key Features

* **Pathway Integration:** scalable vector store and data pipeline backend.
* **Sentence-Aware Chunking:** Uses overlapping windows (approx 1000 words) to preserve narrative context.
* **Character-Focused Search:** Dynamically weights retrieval scores based on character name frequency in the text.
* **Orchestrated Pipeline:** `main.py` handles the full flow from raw text ingestion to CSV result generation.

## 🛠️ Quick Start

### Prerequisites

* Python 3.8+
* Cerebras API Key (for LLM-based judgment)

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt')"

```

### 2. Configure Environment

Create a `.env` file or export your key:

```bash
export CEREBRAS_API_KEY='your-key-here'

```

### 3. Prepare Data

Ensure your directory looks like this:

```
data/
├── novels/         # .txt files (e.g., novel_1.txt)
├── train.csv       # (Optional) For fine-tuning
└── test.csv        # Required: columns [id, book_name, content, char]

```

### 4. Run

**Standard Run (LLM Judgment):**

```bash
python src/main.py --chunk-size 500 --chunk-overlap 100

```

**Fast Run (Heuristics only):**

```bash
python src/main.py --no-llm

```

**Fine-Tune Model:**

```bash
python src/train_embeddings.py

```

## 📊 Output

Results are saved to `results/results.csv` containing:

* `prediction`: 1 (Consistent) or 0 (Inconsistent)
* `rationale`: A generated explanation citing specific evidence.
* `confidence`: The model's certainty score.