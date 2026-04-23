import os
import django
from django.conf import settings
from google import genai

# Setup Django standalone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

client = genai.Client(api_key=settings.GEMINI_API_KEY)
try:
    for m in client.models.list():
        print(f"Model: {m.name}")
        print(f"  Supported methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
