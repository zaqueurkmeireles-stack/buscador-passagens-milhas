import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
print(f"Testing OpenAI key: {key[:10]}...")

client = OpenAI(api_key=key)
try:
    response = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[{"role": "user", "content": "Ping"}]
    )
    print(f"OpenAI Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"OpenAI Error: {e}")
