import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH") or "stepik_killer.db"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# самый дешёвый нормальный grok на openrouter
GPT_MODEL = os.getenv("GPT_MODEL") or "x-ai/grok-4.3"

ADMIN_USER = os.getenv("ADMIN_USER") or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_HOST = os.getenv("ADMIN_HOST") or "0.0.0.0"
ADMIN_PORT = int(os.getenv("ADMIN_PORT") or "8080")
