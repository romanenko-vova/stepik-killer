import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
# состояние диалогов PTB (какая задача открыта). Пользователи и решения — в Postgres
STATE_PATH = os.getenv("STATE_PATH") or "conversation_state.pkl"
# postgresql+asyncpg://user:pass@host:port/db
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+asyncpg://stepik:stepik@127.0.0.1:5434/stepik_killer"
DATABASE_ECHO = (os.getenv("DATABASE_ECHO") or "").lower() in ("1", "true", "yes")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# выбрана по прогону 20 реальных попыток (PROMPT_EVAL.md): смешнее, быстрее и дешевле grok,
# и единственная из версий DeepSeek без пустых ответов
GPT_MODEL = os.getenv("GPT_MODEL") or "deepseek/deepseek-v4.1-flash"

ADMIN_USER = os.getenv("ADMIN_USER") or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_HOST = os.getenv("ADMIN_HOST") or "127.0.0.1"
ADMIN_PORT = int(os.getenv("ADMIN_PORT") or "8080")

# песочница: образ и сколько контейнеров гоняем одновременно
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE") or "python:3.12-slim"
DOCKER_PARALLEL = int(os.getenv("DOCKER_PARALLEL") or "3")

# ревью: лимит ответа и разброс. У grok лимит включает рассуждения — держим запас
REVIEW_MAX_TOKENS = int(os.getenv("REVIEW_MAX_TOKENS") or "1500")
REVIEW_TEMPERATURE = float(os.getenv("REVIEW_TEMPERATURE") or "0.9")

# оффер выключен, пока тексты и ссылка — черновики: включить OFFER_ENABLED=true в .env
OFFER_ENABLED = (os.getenv("OFFER_ENABLED") or "").lower() in ("1", "true", "yes")
# ЧЕРНОВИК: ссылка на пробный урок, поменять на настоящую
TRIAL_URL = os.getenv("TRIAL_URL") or "https://romanenkouchit.ru/?utm_source=nottoxicbot"
# оффер: после стольких решённых задач — сразу
OFFER_AFTER_SOLVED = int(os.getenv("OFFER_AFTER_SOLVED") or "10")
# или через столько дней после старта, если решено хотя бы OFFER_MIN_SOLVED
OFFER_AFTER_DAYS = int(os.getenv("OFFER_AFTER_DAYS") or "3")
OFFER_MIN_SOLVED = int(os.getenv("OFFER_MIN_SOLVED") or "3")
# повтор, если не нажал, и сколько всего раз показываем
OFFER_REPEAT_DAYS = int(os.getenv("OFFER_REPEAT_DAYS") or "7")
OFFER_MAX_SHOWS = int(os.getenv("OFFER_MAX_SHOWS") or "2")

# потолок на одного пользователя в сутки: защищает от тролля и счёт OpenRouter
ATTEMPTS_PER_DAY = int(os.getenv("ATTEMPTS_PER_DAY") or "40")
HINTS_PER_DAY = int(os.getenv("HINTS_PER_DAY") or "20")
