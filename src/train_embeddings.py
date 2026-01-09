"""
train_embeddings.py - Fine-tune the embedding model using train.csv

This script reads the user-provided 'train.csv' file and fine-tunes the
SentenceTransformer model.

Strategy:
We pair the 'character name' with the 'backstory content'.
- Consistent backstories are labeled 1.0 (High Similarity)
- Contradictory backstories are labeled 0.0 (Low Similarity)

This teaches the model to associate the character's identity with their
canonical, true events, and dissociate them from false events.
"""

import pandas as pd
import logging
import os
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def train():
    # Configuration
    TRAIN_FILE = 'train.csv'
    MODEL_NAME = 'all-MiniLM-L6-v2'  # Base model
    OUTPUT_PATH = './fine_tuned_model'
    BATCH_SIZE = 16
    EPOCHS = 3  # Small dataset, so 2-3 epochs is usually safe

    # 1. Load Data
    if not os.path.exists(TRAIN_FILE):
        logger.error(f"File not found: {TRAIN_FILE}")
        print("Please ensure 'train.csv' is in the current directory.")
        return

    logger.info(f"Loading training data from {TRAIN_FILE}...")
    try:
        df = pd.read_csv(TRAIN_FILE)
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        return

    # 2. Prepare Training Examples
    train_examples = []
    skipped_count = 0

    logger.info("Preparing training examples...")
    for index, row in df.iterrows():
        try:
            # Extract fields
            # We use 'char' as the anchor and 'content' as the text to match
            char_name = str(row['char']).strip()
            content = str(row['content']).strip()
            label_str = str(row['label']).strip().lower()

            # Skip incomplete rows
            if not char_name or not content or content == 'nan':
                skipped_count += 1
                continue

            # Determine Score
            # Label 1.0 = Consistent (The text belongs to this character concept)
            # Label 0.0 = Contradict (The text does NOT belong to this character concept)
            if 'consistent' in label_str:
                score = 1.0
            elif 'contradict' in label_str:
                score = 0.0
            else:
                skipped_count += 1
                continue

            # Create InputExample
            # Input A: Character Name
            # Input B: Backstory Claim
            train_examples.append(InputExample(texts=[char_name, content], label=score))

        except KeyError as e:
            logger.error(f"Missing column in CSV: {e}")
            logger.error("Expected columns: 'char', 'content', 'label'")
            return
        except Exception as e:
            skipped_count += 1
            continue

    logger.info(f"Created {len(train_examples)} examples. Skipped {skipped_count} invalid rows.")

    if not train_examples:
        logger.error("No valid examples found to train on. Exiting.")
        return

    # 3. Initialize Model
    logger.info(f"Loading base model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # 4. Create DataLoader
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=BATCH_SIZE)

    # 5. Define Loss Function
    # CosineSimilarityLoss is the standard loss for training with similarity scores
    train_loss = losses.CosineSimilarityLoss(model)

    # 6. Train the Model
    logger.info(f"Starting training for {EPOCHS} epochs...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=EPOCHS,
        warmup_steps=100,
        output_path=OUTPUT_PATH,
        show_progress_bar=True
    )

    logger.info("Training complete!")
    logger.info(f"Model saved to: {os.path.abspath(OUTPUT_PATH)}")
    logger.info("To use this model, update src/embeddings.py to load this path.")

if __name__ == "__main__":
    train()