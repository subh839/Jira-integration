import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai():
    print("Checking environment setup...\n")
    
    # Check .env file
    env_exists = os.path.exists('.env')
    print(f" .env file exists: {env_exists}")
    
    if env_exists:
        with open('.env', 'r') as f:
            env_content = f.read()
        print(f" .env content:\n{env_content}")
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    key_loaded = api_key is not None
    print(f" OPENAI_API_KEY loaded: {key_loaded}")
    
    if key_loaded:
        print(f" API Key found: {api_key[:20]}...")
        
        try:
            # Set the API key (old syntax for v0.28.1)
            openai.api_key = api_key
            
            # Test the API (old syntax)
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello!"}],
                max_tokens=5
            )
            
            print("OpenAI API test: SUCCESS")
            print(f" Response: {response.choices[0].message.content}")
            
        except Exception as e:
            print(f" OpenAI API error: {e}")
            
    # Check library version
    print(f" OpenAI version: {openai.__version__}")

if __name__ == "__main__":
    test_openai()