import json
import os
from dotenv import load_dotenv

load_dotenv()

from app import ai_call, ROADMAP_SYSTEM, safe_json

prompt = "Target Role: Data Scientist\nCurrent Skills: Python, SQL"
try:
    print("Calling AI...")
    raw = ai_call([{"role": "user", "content": prompt}], ROADMAP_SYSTEM, temperature=0.4, max_tokens=4000)
    print(f"Raw Response Length: {len(raw)}")
    print(f"Raw Response Snippet: {raw[:500]}...")
    
    roadmap = safe_json(raw)
    if roadmap:
        print("Success! Roadmap generated and parsed.")
        print(json.dumps(roadmap, indent=2)[:500])
    else:
        print("Failed to parse JSON.")
        with open("failed_response.txt", "w") as f:
            f.write(raw)
        print("Raw response saved to failed_response.txt")
except Exception as e:
    print(f"Error: {e}")
