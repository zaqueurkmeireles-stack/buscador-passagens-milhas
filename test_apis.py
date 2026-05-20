import os, asyncio, httpx
from dotenv import load_dotenv
load_dotenv()

async def testar_apis():
    print('\n=== ?? TESTE FUNCIONAL DE APIs ===')
    async with httpx.AsyncClient() as c:
        try:
            r = await c.get('https://api.openai.com/v1/models', headers={'Authorization': 'Bearer ' + str(os.getenv('OPENAI_API_KEY'))})
            print('  ?? OpenAI: ? OK' if r.status_code == 200 else f'  ?? OpenAI: ? ERRO {r.status_code}')
        except Exception as e: print('  ?? OpenAI: ? FALHA DE REDE')

        try:
            r = await c.get('https://generativelanguage.googleapis.com/v1/models?key=' + str(os.getenv('GOOGLE_GEMINI_API_KEY')))
            print('  ?? Gemini: ? OK' if r.status_code == 200 else f'  ?? Gemini: ? ERRO {r.status_code}')
        except Exception as e: print('  ?? Gemini: ? FALHA DE REDE')

        try:
            r = await c.get(str(os.getenv('SUPABASE_URL')) + '/rest/v1/', headers={'apikey': str(os.getenv('SUPABASE_PUBLISHABLE_KEY'))})
            print('  ??? Supabase: ? OK' if r.status_code == 200 else f'  ??? Supabase: ? ERRO {r.status_code}')
        except Exception as e: print('  ??? Supabase: ? FALHA DE REDE')

        try:
            r = await c.post('https://test.api.amadeus.com/v1/security/oauth2/token', data={'grant_type': 'client_credentials', 'client_id': str(os.getenv('AMADEUS_CLIENT_ID')), 'client_secret': str(os.getenv('AMADEUS_CLIENT_SECRET'))})
            print('  ?? Amadeus: ? OK' if r.status_code == 200 else f'  ?? Amadeus: ? ERRO {r.status_code}')
        except Exception as e: print('  ?? Amadeus: ? FALHA DE REDE')

        try:
            r = await c.get('https://api.duffel.com/air/airlines', headers={'Authorization': 'Bearer ' + str(os.getenv('DUFFEL_API_KEY')), 'Duffel-Version': 'v1'})
            print('  ?? Duffel: ? OK' if r.status_code == 200 else f'  ?? Duffel: ? ERRO {r.status_code}')
        except Exception as e: print('  ?? Duffel: ? FALHA DE REDE')

        try:
            r = await c.get('https://api.telegram.org/bot' + str(os.getenv('TELEGRAM_BOT_TOKEN')) + '/getMe')
            print('  ?? Telegram: ? OK' if r.status_code == 200 else f'  ?? Telegram: ? ERRO {r.status_code}')
        except Exception as e: print('  ?? Telegram: ? FALHA DE REDE')

    print('==================================\n')

asyncio.run(testar_apis())
