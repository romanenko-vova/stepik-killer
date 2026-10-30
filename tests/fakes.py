"""Минимальные заглушки Telegram: хватает, чтобы прогнать хендлер и посмотреть, что он отправил."""

from types import SimpleNamespace


class FakeMessage:
    def __init__(self, bot, chat_id, text="", message_id=1):
        self.bot = bot
        self.chat_id = chat_id
        self.text = text
        self.message_id = message_id

    async def reply_text(self, text, **kwargs):
        return await self.bot.send_message(chat_id=self.chat_id, text=text, **kwargs)

    async def edit_text(self, text, **kwargs):
        self.bot.sent.append({"edit": True, "text": text, **kwargs})
        return self

    async def delete(self):
        return True


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append({"chat_id": chat_id, "text": text, **kwargs})
        return FakeMessage(self, chat_id, text, message_id=len(self.sent))

    async def edit_message_text(self, chat_id, message_id, text, **kwargs):
        self.sent.append({"edit": True, "chat_id": chat_id, "text": text, **kwargs})

    async def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        self.sent.append({"edit_markup": True, "chat_id": chat_id, "text": "", "reply_markup": reply_markup})

    async def send_chat_action(self, chat_id, action):
        return True

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        self.sent.append({"chat_id": chat_id, "photo": True, "text": caption})


class FakeQuery:
    def __init__(self, bot, chat_id, data):
        self.data = data
        self.message = FakeMessage(bot, chat_id)
        self.bot = bot

    async def answer(self, *args, **kwargs):
        return True

    async def edit_message_text(self, text, **kwargs):
        self.bot.sent.append({"edit": True, "text": text, **kwargs})


def make_update(tg_id=777, text=None, data=None, bot=None, username="kid", first_name="Кид"):
    bot = bot or FakeBot()
    user = SimpleNamespace(id=tg_id, username=username, first_name=first_name)
    chat = SimpleNamespace(id=tg_id)
    message = FakeMessage(bot, tg_id, text) if text is not None else None
    query = FakeQuery(bot, tg_id, data) if data is not None else None
    update = SimpleNamespace(effective_user=user, effective_chat=chat, message=message, callback_query=query)
    return update, bot


def make_context(bot, args=None, user_data=None):
    return SimpleNamespace(bot=bot, args=args or [], user_data=user_data if user_data is not None else {})
