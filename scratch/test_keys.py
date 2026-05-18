import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

key = os.getenv("GOOGLE_GEMINI_API_KEY")
print(f"Testing key: {key[:10]}...")

genai.configure(api_key=key)
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Ping")
    print(f"Gemini 1.5 Flash Response: {response.text}")
except Exception as e:
    print(f"Gemini 1.5 Flash Error: {e}")

try:
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content("Ping")
    print(f"Gemini 1.5 Pro Response: {response.text}")
except Exception as e:
    print(f"Gemini 1.5 Pro Error: {e}")
