from google import genai
import traceback

print("Listing models...")
try:
    client = genai.Client(api_key="AIzaSyArj4tkun-XjrcbU9GfX_YNYj-XUKZ-BuM")
    pager = client.models.list()
    for model in pager:
        print(model.name)
except Exception as e:
    print(f"Failed to list models: {e}")
    traceback.print_exc()
