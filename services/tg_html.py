import html

# Telegram из всего HTML понимает только эти четыре тега
OK_TAGS = ("b", "i", "code", "pre")


def read_tag_name(tag: str):
    """Из '<b>' / '</code>' / '<br/>' достаём имя и флаг 'это закрывающий?'."""
    inner = tag[1:-1].strip()
    if inner.endswith("/"):
        inner = inner[:-1].strip()

    closing = inner.startswith("/")
    if closing:
        inner = inner[1:].strip()

    if not inner:
        return "", closing

    name = inner.split()[0].lower()
    return name, closing


def split_into_text_and_tags(text: str):
    """Режем строку на куски: обычный текст и куски в угловых скобках."""
    chunks = []
    i = 0
    while i < len(text):
        if text[i] != "<":
            next_bracket = text.find("<", i)
            if next_bracket == -1:
                chunks.append(("text", text[i:]))
                break
            chunks.append(("text", text[i:next_bracket]))
            i = next_bracket
            continue

        close_bracket = text.find(">", i)
        if close_bracket == -1:
            # скобку открыли, но не закрыли — это уже не тег, а текст
            chunks.append(("text", text[i:]))
            break

        tag = text[i : close_bracket + 1]
        name, _ = read_tag_name(tag)
        # "x < 10>" — это не html, а сравнение в коде, оставляем как текст
        if not name.isalpha():
            chunks.append(("text", text[i]))
            i += 1
            continue

        chunks.append(("tag", tag))
        i = close_bracket + 1
    return chunks


def clean_tg_html(text: str) -> str:
    """
    Готовим HTML к отправке в Telegram.

    GPT любит вставлять <br>, лишние </b> и куски кода с символом <.
    Telegram от такого падает, поэтому:
    1. <br> превращаем в обычный перенос строки
    2. оставляем только b / i / code / pre
    3. закрываем теги в правильном порядке
    4. символы < и > в обычном тексте экранируем
    """
    result = []
    open_tags = []  # стопка открытых тегов, как тарелки: верхний закрываем первым

    for kind, chunk in split_into_text_and_tags(text):
        if kind == "text":
            result.append(html.escape(chunk))
            continue

        name, closing = read_tag_name(chunk)

        if name == "br":
            result.append("\n")
            continue

        if name not in OK_TAGS:
            continue

        if not closing:
            open_tags.append(name)
            result.append(f"<{name}>")
            continue

        # закрывающий тег без открытия — просто выкидываем
        if name not in open_tags:
            continue

        # если сверху другая тарелка — сначала закрываем её
        while open_tags and open_tags[-1] != name:
            result.append(f"</{open_tags.pop()}>")
        open_tags.pop()
        result.append(f"</{name}>")

    # что открыли и забыли закрыть — закрываем сами
    while open_tags:
        result.append(f"</{open_tags.pop()}>")

    return "".join(result)


def fit_tg_html(text: str, limit: int) -> str:
    """Ужимаем текст под лимит Telegram, не ломая теги посередине."""
    text = clean_tg_html(text)
    if len(text) <= limit:
        return text
    return clean_tg_html(text[:limit] + "…")
