import sys
from pathlib import Path
import os

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.core.search.llm_interface import LLMInterface
from backend.core.search.dialog_search import DialogSearchSystem

def test_search_system():
    """Test the dialog search system functionality"""
    config_path = Path(project_root) / "config" / "app_config.yaml"
    
    print("\n=== Testing Dialog Search System ===")
    print(f"Using config from: {config_path}")
    
    try:
        # Initialize LLM interface
        llm = LLMInterface(str(config_path))
        print("\nLLM interface initialized successfully")
        
        # Test dialog generation and matching
        test_input = "Tell me about the nature of consciousness"
        print(f"\nTesting with input: {test_input}")
        
        response, matches = llm.generate_and_match(test_input)
        print(f"\nGenerated response: {response}")
        print(f"Found {len(matches)} potential matches")
        
        if matches:
            print("\nFirst match:")
            text, metadata = matches[0]
            print(f"Text: {text}")
            print(f"Metadata: {metadata}")
            
            # Test best match selection
            best_idx = llm.select_best_match(test_input, matches)
            if best_idx >= 0:
                print(f"\nBest match index: {best_idx}")
                best_text, best_metadata = matches[best_idx]
                print(f"Best match text: {best_text}")
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        raise

if __name__ == "__main__":
    test_search_system() 