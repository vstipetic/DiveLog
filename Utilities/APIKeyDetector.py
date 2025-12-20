import os
from typing import Dict

def detect_api_keys() -> Dict[str, str]:
    """
    Scans environment variables for available LLM API keys.
    Currently checks for OpenAI and Google/Gemini API keys.
    
    Returns:
        Dict[str, str]: Dictionary mapping service names to their API keys
    """
    available_apis = {}
    
    # Check for OpenAI API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        available_apis['OpenAI'] = openai_key
    
    # Check for Google/Gemini API key
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        available_apis['Gemini'] = gemini_key
        
    if not available_apis:
        print("Warning: No API keys found in environment variables")
        # Add a dummy API for testing
        available_apis['Test API'] = 'dummy_key'
    
    return available_apis 