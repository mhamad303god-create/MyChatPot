from google import genai
from google.genai import types
import traceback

print("Testing Gemini connection with Lite model...")
client = genai.Client(api_key="AIzaSyArj4tkun-XjrcbU9GfX_YNYj-XUKZ-BuM")

try:
    print("Trying gemini-2.5-flash-lite-preview-09-2025...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-09-2025",
        config=types.GenerateContentConfig(
            system_instruction="Hello",
        ),
        contents="Hi, are you working?",
    )
    print("Success!")
    print(response.text)
except Exception as e:
    print(f"Failed: {e}")
    traceback.print_exc()
