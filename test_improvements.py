#!/usr/bin/env python3
"""Quick test script for PubMed improvements."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pubmed():
    """Test PubMed search improvements."""
    
    try:
        from src.tools.pubmed_tool import PubMedTool
        from src.config import settings
    except Exception as e:
        print(f"Error importing modules: {e}")
        print("\nMake sure you have installed dependencies:")
        print("  pip install -r requirements.txt")
        print("\nAnd configured your .env file with API keys")
        return
    
    print("=" * 80)
    print("Testing PubMed Tool Improvements")
    print("=" * 80)
    
    tool = PubMedTool()
    
    # Test 1: Simple disease name (previously failed)
    print("\n[TEST 1] Searching for 'Lupus'...")
    print("-" * 80)
    try:
        results1 = tool.search("Lupus")
        print(f"✓ Found {len(results1)} results")
        
        if results1:
            print(f"\nTop 3 results:")
            for i, r in enumerate(results1[:3], 1):
                print(f"\n  [{i}] {r.title[:80]}...")
                print(f"      Relevance: {r.relevance_score:.2f}")
                print(f"      Year: {r.metadata.get('year', 'N/A')}")
                print(f"      Proteins: {', '.join(r.metadata.get('proteins_mentioned', [])[:5])}")
                print(f"      URL: {r.metadata.get('url', 'N/A')}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Full disease name
    print("\n\n[TEST 2] Searching for 'Systemic Lupus Erythematosus'...")
    print("-" * 80)
    try:
        results2 = tool.search("Systemic Lupus Erythematosus")
        print(f"✓ Found {len(results2)} results")
        
        if results2:
            print(f"\nHighest relevance result:")
            r = sorted(results2, key=lambda x: x.relevance_score, reverse=True)[0]
            print(f"  Title: {r.title}")
            print(f"  Relevance: {r.relevance_score:.2f}")
            print(f"  Year: {r.metadata.get('year', 'N/A')}")
            print(f"  Pub Types: {', '.join(r.metadata.get('publication_types', [])[:2])}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: With protein context
    print("\n\n[TEST 3] Searching for 'Lupus' with protein 'IFNA'...")
    print("-" * 80)
    try:
        results3 = tool.search("Lupus", "IFNA")
        print(f"✓ Found {len(results3)} results")
        
        if results3:
            print(f"\nTargeted result sample:")
            r = results3[0]
            print(f"  Title: {r.title[:80]}...")
            print(f"  Relevance: {r.relevance_score:.2f}")
            print(f"  Proteins mentioned: {', '.join(r.metadata.get('proteins_mentioned', [])[:5])}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Testing complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_pubmed()
