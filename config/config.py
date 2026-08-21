import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH") or "stepik_killer.db"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# самый дешёвый нормальный grok на openrouter
GPT_MODEL = os.getenv("GPT_MODEL") or "x-ai/grok-4.3"
