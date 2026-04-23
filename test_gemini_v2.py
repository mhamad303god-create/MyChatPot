from google import genai
from google.genai import types
import traceback

print("Testing Gemini connection with correct model names...")
client = genai.Client(api_key="AIzaSyArj4tkun-XjrcbU9GfX_YNYj-XUKZ-BuM")

try:
    print("Trying gemini-2.5-flash-preview-09-2025...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-09-2025",
        config=types.GenerateContentConfig(
            system_instruction="Hello",
        ),
        contents="Hi",
    )
    print("Success with gemini-2.5-flash-preview-09-2025")
    print(response.text)
except Exception as e:
    print(f"Failed with gemini-2.5-flash-preview-09-2025: {e}")
    traceback.print_exc()

try:
    print("Trying gemini-3-flash-preview...")
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            system_instruction="Hello",
        ),
        contents="Hi",
    )
    print("Success with gemini-3-flash-preview")
    print(response.text)
except Exception as e:
    print(f"Failed with gemini-3-flash-preview: {e}")
    traceback.print_exc()
