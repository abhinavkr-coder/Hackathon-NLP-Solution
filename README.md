
# Narrative Consistency Checker (NLP Hackathon Solution)

This project is an automated pipeline designed to evaluate whether a character's backstory is consistent with the narrative events of a novel. It utilizes a fine-tuned embedding model for semantic retrieval and an LLM-based judge to detect hallucinations and contradictions.

## 📋 Prerequisites & Installation

### 1. System Requirements

* **Python 3.8+**
* **Cerebras API Key** (Required for the LLM judge)

### 2. Install Dependencies

All required libraries are listed in `requirements.txt`. Install them using pip:

```bash
pip install -r requirements.txt

```

This will install key dependencies like `pathway`, `torch`, `sentence-transformers`, `pandas`, and `openai`.

### 3. Environment Setup

Create a `.env` file in the root directory to store your API key. The system uses this to authenticate the LLM judge.

**File:** `.env`

```text
CEREBRAS_API_KEY=your_actual_api_key_here

```

### 4. Folder Structure

Ensure your data is organized as follows so the scripts can locate the files:

```text
root/
├── data/
│   ├── novels/             # Place your novel text files (.txt) here
│   └── test.csv            # CSV containing backstories to evaluate
├── train.csv               # CSV containing training pairs for the model
├── requirements.txt        # Dependency list
├── .env                    # API Key file
├── main.py                 # Main pipeline script
├── train_embeddings.py     # Training script
└── ... (other python modules)

```

## 🚀 How to Run

You must follow this specific order to generate the custom model before running the evaluation.

### Step 1: Train the Embedding Model

First, run the training script. This fine-tunes the base model using your `train.csv` data to better understand consistency vs. contradiction.

```bash
python train_embeddings.py

```

* **Output:** This creates a directory named `./fine_tuned_model` containing your custom model.

### Step 2: Run the Main Pipeline

Once the model is trained, run the main script. This orchestrates the entire process: preprocessing novels, creating embeddings, retrieving evidence, and generating the final judgment.

```bash
python src/main.py --chunk-size 500 --chunk-overlap 100

```

* **Note:** This script will automatically use the model created in Step 1 found in `./fine_tuned_model`.

---

## 📂 Output Results

After the execution finishes, the results will be saved in the **`results/`** directory:

* **`results.csv`**: Contains the final consistency predictions, confidence scores, and rationales for each test case.