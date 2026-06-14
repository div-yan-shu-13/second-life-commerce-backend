"""List available Gemini models."""
from dotenv import load_dotenv
import os
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(model.name)
