import google.generativeai as genai
import sys

# Configure Google Gemini API with your API key
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)genai.configure(api_key=API_KEY)

def test_api_connection():
    """Test if the Google Generative AI API is working properly"""
    print("Testing Google Generative AI API connection...")
    
    # List all available models to see what's available
    try:
        print("\nListing available models:")
        for model in genai.list_models():
            if "generateContent" in model.supported_generation_methods:
                print(f"- {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
        return False
    
    # Try to use the model
    try:
        print("\nTesting model response:")
        # Try with gemini-1.5-pro first
        model_names = [
            "gemini-1.5-pro", 
            "gemini-pro", 
            "gemini-pro-vision"
        ]
        
        for model_name in model_names:
            print(f"\nTrying model: {model_name}")
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello, what's the capital of France?")
                
                if hasattr(response, "text"):
                    print(f"Response received: {response.text[:100]}...")
                    print(f"SUCCESS: Model {model_name} works!")
                    return True
                else:
                    print(f"Model {model_name} didn't return a text response.")
            except Exception as model_error:
                print(f"Error with model {model_name}: {model_error}")
        
        print("ERROR: None of the tested models worked.")
        return False
        
    except Exception as e:
        print(f"Error testing model: {e}")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    if success:
        print("\nAPI TEST SUCCESSFUL: The Google Generative AI API is working correctly!")
        sys.exit(0)
    else:
        print("\nAPI TEST FAILED: There was an issue with the Google Generative AI API.")
        print("Please check your API key and internet connection.")
        sys.exit(1)