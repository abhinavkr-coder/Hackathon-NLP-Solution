import os
import sys
import json
from pathlib import Path

# Make src importable (when run from repo root)
sys.path.insert(0, os.path.abspath('.'))

from main import NarrativeConsistencySystem


def run_and_collect(use_llm: bool, data_dir: str = './data', results_dir: str = './results') -> dict:
    system = NarrativeConsistencySystem(data_dir=data_dir, results_dir=results_dir, use_llm=use_llm)

    # Process novels (build embeddings/index)
    system.process_novels()

    # Run evaluation
    df = system.run_evaluation()

    # Compute metrics
    metrics = {}
    metrics['method'] = 'llm' if use_llm else 'heuristic'
    metrics['total'] = len(df)
    if 'prediction' in df.columns:
        metrics['count_1'] = int((df['prediction'] == 1).sum())
        metrics['count_0'] = int((df['prediction'] == 0).sum())
    else:
        metrics['count_1'] = 0
        metrics['count_0'] = 0

    # confidences
    if 'confidence' in df.columns and len(df) > 0:
        metrics['avg_confidence'] = float(df['confidence'].mean())
        # avg per label
        if metrics['count_1'] > 0:
            metrics['avg_confidence_1'] = float(df[df['prediction'] == 1]['confidence'].mean())
            metrics['best_confidence_1'] = float(df[df['prediction'] == 1]['confidence'].max())
        else:
            metrics['avg_confidence_1'] = None
            metrics['best_confidence_1'] = None

        if metrics['count_0'] > 0:
            metrics['avg_confidence_0'] = float(df[df['prediction'] == 0]['confidence'].mean())
            metrics['best_confidence_0'] = float(df[df['prediction'] == 0]['confidence'].max())
        else:
            metrics['avg_confidence_0'] = None
            metrics['best_confidence_0'] = None
    else:
        metrics['avg_confidence'] = None
        metrics['avg_confidence_1'] = None
        metrics['avg_confidence_0'] = None
        metrics['best_confidence_1'] = None
        metrics['best_confidence_0'] = None

    # Save metrics
    out_file = Path(results_dir) / f"metrics_{metrics['method']}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved metrics to {out_file}")
    return metrics


def main():
    data_dir = './data'
    results_dir = './results'

    print('Running heuristic (no LLM) evaluation...')
    metrics_no_llm = run_and_collect(use_llm=False, data_dir=data_dir, results_dir=results_dir)

    print('Running LLM-enabled evaluation...')
    metrics_llm = run_and_collect(use_llm=True, data_dir=data_dir, results_dir=results_dir)

    summary = {
        'no_llm': metrics_no_llm,
        'llm': metrics_llm
    }

    with open(Path(results_dir) / 'comparison_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print('Comparison complete. Summary saved to results/comparison_summary.json')


if __name__ == '__main__':
    main()
