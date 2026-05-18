import os
from dotenv import load_dotenv
import httpx
import asyncio

load_dotenv()

async def test_amadeus():
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    print(f"Testing Amadeus: {client_id[:5]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://test.api.amadeus.com/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=10,
            )
            resp.raise_for_status()
            print("Amadeus Token: SUCCESS")
        except Exception as e:
            print(f"Amadeus Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_amadeus())
