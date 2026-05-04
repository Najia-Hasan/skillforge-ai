import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
print(f"Using API Key: {api_key[:10]}...")

client = Groq(api_key=api_key)
try:
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    print(f"API Call Success: {resp.choices[0].message.content}")
except Exception as e:
    print(f"API Call Failed: {e}")
