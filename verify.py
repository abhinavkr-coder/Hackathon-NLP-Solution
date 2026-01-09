#!/usr/bin/env python3
"""
Verification script for Hackathon NLP Solution
Checks all components and verifies system readiness
"""

import sys
import os
from glob import glob

# Add src to path
sys.path.insert(0, 'src')

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_check(status, message):
    """Print a check result"""
    symbol = "[OK]" if status else "[FAIL]"
    print(f"{symbol} {message}")
    return status

def check_imports():
    """Check if all required modules can be imported"""
    print_header("CHECKING IMPORTS")
    
    all_ok = True
    
    try:
        from judge import ConsistencyJudge
        print_check(True, "judge.py imports successfully")
    except Exception as e:
        print_check(False, f"judge.py import failed: {e}")
        all_ok = False
    
    try:
        from embeddings import EmbeddingManager, PathwayVectorStore
        print_check(True, "embeddings.py imports successfully")
    except Exception as e:
        print_check(False, f"embeddings.py import failed: {e}")
        all_ok = False
    
    try:
        from preprocess import NovelPreprocessor, preprocess_backstory
        print_check(True, "preprocess.py imports successfully")
    except Exception as e:
        print_check(False, f"preprocess.py import failed: {e}")
        all_ok = False
    
    try:
        from retrieve import EvidenceRetriever
        print_check(True, "retrieve.py imports successfully")
    except Exception as e:
        print_check(False, f"retrieve.py import failed: {e}")
        all_ok = False
    
    try:
        from main import NarrativeConsistencySystem
        print_check(True, "main.py imports successfully")
    except Exception as e:
        print_check(False, f"main.py import failed: {e}")
        all_ok = False
    
    return all_ok

def check_initialization():
    """Check if all components can be initialized"""
    print_header("CHECKING INITIALIZATION")
    
    all_ok = True
    
    try:
        from judge import ConsistencyJudge
        judge = ConsistencyJudge(use_llm=False)
        print_check(True, "ConsistencyJudge initialized (heuristic mode)")
    except Exception as e:
        print_check(False, f"ConsistencyJudge initialization failed: {e}")
        all_ok = False
    
    try:
        from preprocess import NovelPreprocessor
        preprocessor = NovelPreprocessor(chunk_size=100, overlap=20)
        print_check(True, "NovelPreprocessor initialized")
    except Exception as e:
        print_check(False, f"NovelPreprocessor initialization failed: {e}")
        all_ok = False
    
    try:
        from embeddings import EmbeddingManager
        em = EmbeddingManager()
        print_check(True, "EmbeddingManager initialized")
    except Exception as e:
        print_check(False, f"EmbeddingManager initialization failed: {e}")
        all_ok = False
    
    try:
        from embeddings import EmbeddingManager, PathwayVectorStore
        em = EmbeddingManager()
        vs = PathwayVectorStore(em)
        print_check(True, "PathwayVectorStore initialized")
    except Exception as e:
        print_check(False, f"PathwayVectorStore initialization failed: {e}")
        all_ok = False
    
    return all_ok

def check_data_files():
    """Check if required data files exist"""
    print_header("CHECKING DATA FILES")
    
    all_ok = True
    
    # Check data directory
    if os.path.isdir("data"):
        print_check(True, "data/ directory exists")
    else:
        print_check(False, "data/ directory not found")
        all_ok = False
    
    # Check novels directory
    if os.path.isdir("data/novels"):
        novel_files = list(glob("data/novels/*.txt"))
        if novel_files:
            print_check(True, f"data/novels/ contains {len(novel_files)} novel file(s)")
        else:
            print_check(False, "data/novels/ is empty")
            all_ok = False
    else:
        print_check(False, "data/novels/ directory not found")
        all_ok = False
    
    # Check test.csv
    if os.path.isfile("data/test.csv"):
        print_check(True, "data/test.csv exists")
    else:
        print_check(False, "data/test.csv not found (required for execution)")
        all_ok = False
    
    # Check results directory can be created
    results_dir = "results"
    if not os.path.isdir(results_dir):
        try:
            os.makedirs(results_dir, exist_ok=True)
            print_check(True, f"{results_dir}/ directory created/exists")
        except Exception as e:
            print_check(False, f"Cannot create {results_dir}/: {e}")
            all_ok = False
    else:
        print_check(True, f"{results_dir}/ directory exists")
    
    return all_ok

def check_dependencies():
    """Check if required packages are installed"""
    print_header("CHECKING DEPENDENCIES")
    
    required_packages = [
        ('groq', 'Groq API client'),
        ('dotenv', 'Environment variables'),
        ('sentence_transformers', 'Sentence embeddings'),
        ('nltk', 'Text tokenization'),
        ('pandas', 'Data handling'),
        ('numpy', 'Numerical operations'),
        ('pathway', 'Vector operations'),
    ]
    
    all_ok = True
    
    for package_name, description in required_packages:
        try:
            __import__(package_name)
            print_check(True, f"{package_name:25} - {description}")
        except ImportError:
            print_check(False, f"{package_name:25} - {description} (NOT FOUND)")
            all_ok = False
    
    return all_ok

def check_env_file():
    """Check if .env.example exists"""
    print_header("CHECKING ENVIRONMENT SETUP")
    
    all_ok = True
    
    if os.path.isfile(".env.example"):
        print_check(True, ".env.example exists (configuration template)")
    else:
        print_check(False, ".env.example not found")
        all_ok = False
    
    if os.path.isfile(".env"):
        print_check(True, ".env exists (your local configuration)")
    else:
        print_check(False, ".env not found (create with: cp .env.example .env)")
        all_ok = False
    
    return all_ok

def print_summary(results):
    """Print final summary"""
    print_header("VERIFICATION SUMMARY")
    
    checks = [
        ("Module Imports", results["imports"]),
        ("Component Initialization", results["initialization"]),
        ("Data Files", results["data"]),
        ("Dependencies", results["dependencies"]),
        ("Environment Setup", results["env"]),
    ]
    
    all_passed = all(r for _, r in checks)
    
    for name, passed in checks:
        symbol = "[PASS]" if passed else "[FAIL]"
        print(f"{symbol} {name}")
    
    print(f"\n{'='*60}")
    
    if all_passed:
        print("  STATUS: ALL CHECKS PASSED - Ready to run!")
        print("\n  Run the pipeline with:")
        print("  python src/main.py --no-llm")
        print("  or")
        print("  python src/main.py --use-llm")
    else:
        print("  STATUS: SOME CHECKS FAILED - See above for details")
        print("\n  Fix any issues marked [FAIL] before running")
    
    print(f"{'='*60}\n")
    
    return all_passed

def main():
    """Run all verification checks"""
    print("\n" + "="*60)
    print("  Narrative Consistency System - Verification Script")
    print("="*60)
    
    results = {
        "imports": check_imports(),
        "initialization": check_initialization(),
        "data": check_data_files(),
        "dependencies": check_dependencies(),
        "env": check_env_file(),
    }
    
    success = print_summary(results)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
