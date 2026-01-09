#!/usr/bin/env python3
"""
Test script to verify enhanced LLM judgment with aggressive confidence calibration.
Shows the improvement from enhanced prompts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from judge import ConsistencyJudge
import json
from datetime import datetime

def test_enhanced_llm():
    """Test the enhanced LLM judgment with aggressive confidence calibration."""
    
    print("=" * 80)
    print("TESTING ENHANCED LLM JUDGMENT WITH AGGRESSIVE CONFIDENCE CALIBRATION")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize judge with LLM enabled
    judge = ConsistencyJudge(use_llm=True)
    
    test_cases = [
        {
            "name": "Test 1: Wealth vs Poverty (CONTRADICTION)",
            "backstory": "John was born wealthy and inherited a private hospital from his family.",
            "evidence": [
                {
                    'text': "John remembered the cold winters in his childhood home, where heating was a luxury they couldn't afford due to their extreme poverty.",
                    'similarity': 0.92
                },
                {
                    'text': "His childhood was marked by financial struggle and hardship.",
                    'similarity': 0.85
                }
            ],
            "expected_prediction": 0,
            "expected_confidence": "0.85+"
        },
        {
            "name": "Test 2: London Poverty (CONSISTENT)",
            "backstory": "John grew up in poverty in London during the 1970s.",
            "evidence": [
                {
                    'text': "John remembered the cold winters in his childhood home in London, where heating was a luxury they couldn't afford.",
                    'similarity': 0.90
                },
                {
                    'text': "The poverty of his London upbringing shaped his determination to succeed.",
                    'similarity': 0.88
                },
                {
                    'text': "Growing up poor in London taught him resilience.",
                    'similarity': 0.82
                }
            ],
            "expected_prediction": 1,
            "expected_confidence": "0.85+"
        },
        {
            "name": "Test 3: Medical Doctor (CONSISTENT)",
            "backstory": "Sarah always dreamed of becoming a doctor, inspired by her mother's compassionate care.",
            "evidence": [
                {
                    'text': "Sarah's mother was a nurse, and Sarah grew up watching her care for patients with kindness.",
                    'similarity': 0.87
                },
                {
                    'text': "She pursued medical school with determination, driven by memories of her mother's compassion.",
                    'similarity': 0.85
                },
                {
                    'text': "Sarah became a respected physician known for treating patients with empathy.",
                    'similarity': 0.83
                }
            ],
            "expected_prediction": 1,
            "expected_confidence": "0.90+"
        },
        {
            "name": "Test 4: War Hero (INCONSISTENT - No Evidence)",
            "backstory": "Michael was a decorated military general who commanded thousands of troops in World War II.",
            "evidence": [
                {
                    'text': "Michael worked as a librarian his entire adult life, surrounded by books.",
                    'similarity': 0.21
                },
                {
                    'text': "He was known for his quiet demeanor and love of reading.",
                    'similarity': 0.19
                }
            ],
            "expected_prediction": 0,
            "expected_confidence": "0.80+"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test_case['name']}")
        print(f"{'='*80}")
        
        backstory = test_case['backstory']
        evidence = test_case['evidence']
        expected_pred = test_case['expected_prediction']
        
        print(f"\nBackstory: {backstory}")
        print(f"\nEvidence ({len(evidence)} pieces):")
        for j, e in enumerate(evidence, 1):
            print(f"  {j}. [{e['similarity']:.2f}] {e['text'][:70]}...")
        
        try:
            print("\n⏳ Calling enhanced LLM judgment...")
            prediction, rationale, confidence = judge.judge_consistency(
                backstory, evidence, f"test_{i}"
            )
            
            print(f"\n✓ LLM Response received:")
            print(f"  Prediction: {prediction} (Expected: {expected_pred})")
            print(f"  Confidence: {confidence:.3f} (Expected: {test_case['expected_confidence']})")
            print(f"  Rationale: {rationale}")
            
            # Verify correctness
            correct = prediction == expected_pred
            confidence_good = confidence >= 0.80  # Look for high confidence
            
            result = {
                "test": test_case['name'],
                "prediction": prediction,
                "confidence": round(confidence, 3),
                "expected_pred": expected_pred,
                "correct": correct,
                "confidence_high": confidence_good,
                "rationale": rationale[:100] + "..." if len(rationale) > 100 else rationale
            }
            results.append(result)
            
            status = "✓ PASS" if (correct and confidence_good) else "⚠ REVIEW"
            print(f"\nStatus: {status}")
            if not correct:
                print(f"  ⚠ Prediction mismatch: got {prediction}, expected {expected_pred}")
            if not confidence_good:
                print(f"  ⚠ Confidence low: {confidence:.3f} < 0.80")
            
        except Exception as e:
            print(f"\n✗ Error during judgment: {e}")
            result = {
                "test": test_case['name'],
                "prediction": None,
                "confidence": None,
                "error": str(e)
            }
            results.append(result)
            print("Note: This might be due to API rate limits. Check Groq API status.")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    successful = [r for r in results if 'error' not in r]
    errors = [r for r in results if 'error' in r]
    
    if successful:
        correct_predictions = sum(1 for r in successful if r.get('correct'))
        high_confidence = sum(1 for r in successful if r.get('confidence_high'))
        
        print(f"\nTests completed: {len(successful)}/{len(results)}")
        print(f"Correct predictions: {correct_predictions}/{len(successful)} ({100*correct_predictions/len(successful):.0f}%)")
        print(f"High confidence (0.80+): {high_confidence}/{len(successful)} ({100*high_confidence/len(successful):.0f}%)")
        print(f"Average confidence: {sum(r['confidence'] for r in successful)/len(successful):.3f}")
        
        print("\nDetailed Results:")
        for r in successful:
            pred_status = "✓" if r['correct'] else "✗"
            conf_status = "✓" if r['confidence_high'] else "⚠"
            print(f"  {pred_status} {conf_status} {r['test']}: conf={r['confidence']:.3f}")
    
    if errors:
        print(f"\n⚠ Errors: {len(errors)} tests failed with exceptions")
        for r in errors:
            print(f"  - {r['test']}: {r['error'][:50]}...")
    
    print(f"\n{'='*80}")
    print("Enhanced LLM test complete. Check confidence levels (should be 0.80+)")
    print(f"{'='*80}\n")
    
    return results

if __name__ == "__main__":
    results = test_enhanced_llm()
    
    # Save results
    with open('llm_boost_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Results saved to llm_boost_test_results.json")
