import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('TELEGRAM_TOKEN')
api_key = os.getenv('BINANCE_API_KEY')

print(f"Telegram Token: {'✅ SET' if token else '❌ MISSING'}")
print(f"Token length: {len(token) if token else 0}")
if token:
    print(f"Token starts with: {token[:10]}...")
    
print(f"Binance API Key: {'✅ SET' if api_key else '❌ MISSING'}")
