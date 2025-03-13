import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.config.settings import get_settings

def test_config():
    try:
        # Try loading settings
        settings = get_settings()
        
        # Print some values to verify
        print("Configuration Test Results:")
        print("-" * 50)
        
        # Test app config
        print("App Config loaded:", bool(settings.app_config))
        if settings.app_config:
            print("Sample app_config value (paths):", settings.app_config.get('paths', {}))
        
        # Test prompts config
        print("\nPrompts Config loaded:", bool(settings.prompts_config))
        if settings.prompts_config:
            print("Sample prompts_config keys:", list(settings.prompts_config.keys())[:3])
        
        # Test search config
        print("\nSearch Config loaded:", bool(settings.search_config))
        if settings.search_config:
            print("Sample search_config value (gemini):", settings.search_config.get('gemini', {}))
        
        print("\nAll configurations loaded successfully!")
        
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_config() 