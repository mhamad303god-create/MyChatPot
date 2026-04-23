from google import genai
from google.genai import types
import traceback

print("Testing Gemini connection...")
try:
    client = genai.Client(api_key="AIzaSyArj4tkun-XjrcbU9GfX_YNYj-XUKZ-BuM")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="Hello",
        ),
        contents="Hi",
    )
    print("Success with gemini-2.5-flash")
    print(response.text)
except Exception as e:
    print(f"Failed with gemini-2.5-flash: {e}")
    # Try 1.5-flash
    try:
        print("Trying gemini-1.5-flash...")
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config=types.GenerateContentConfig(
                system_instruction="Hello",
            ),
            contents="Hi",
        )
        print("Success with gemini-1.5-flash")
        print(response.text)
    except Exception as e2:
         print(f"Failed with gemini-1.5-flash: {e2}")
         traceback.print_exc()
