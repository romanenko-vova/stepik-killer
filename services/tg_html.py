import html
import re

# Telegram из всего HTML понимает только эти четыре тега
OK_TAGS = ("b", "i", "code", "pre")

# кавычки в тг не экранируем — иначе в чате торчит &quot;
QUOTE_ENTS = (
    ("&quot;", '"'),
    ("&#34;", '"'),
    ("&#x22;", '"'),
    ("&#x27;", "'"),
    ("&#39;", "'"),
    ("&apos;", "'"),
)


def decode_entities(text: str) -> str:
    # gpt часто пишет &quot; вместо кавычек — возвращаем нормальные символы
    prev = None
    while prev != text:
        prev = text
        text = html.unescape(text)
    return text


def escape_tg_text(text: str) -> str:
    # в тг кавычки экранировать не надо, иначе ученик видит &quot;
    return html.escape(decode_entities(text), quote=False)


def restore_quotes(text: str) -> str:
    # на всякий случай, если сущность пролезла после чистки
    for ent, ch in QUOTE_ENTS:
        text = text.replace(ent, ch)
    return text


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
            result.append(escape_tg_text(chunk))
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


def prepare_tg_html(text: str, limit: int | None = None) -> str:
    """Финальный текст в чат: валидные теги, живые кавычки, без двойного экранирования."""
    text = restore_quotes(clean_tg_html(text))
    if limit is not None and len(text) > limit:
        text = restore_quotes(clean_tg_html(text[:limit] + "…"))
    return text


def fit_tg_html(text: str, limit: int) -> str:
    """Ужимаем текст под лимит Telegram, не ломая теги посередине."""
    return prepare_tg_html(text, limit)


_BARE_AMP = re.compile(r"&(?!amp;|lt;|gt;|#\d+;|#x[0-9a-fA-F]+;)")


def tg_html_problems(text: str) -> list[str]:
    # ловим то, из-за чего в чате каша или Telegram режет сообщение
    problems = []
    for bad in ("&amp;quot;", "&amp;lt;", "&amp;gt;", "&quot;", "&#34;", "&apos;"):
        if bad in text:
            problems.append(bad)
    if _BARE_AMP.search(text):
        problems.append("голый &")
    open_tags = []
    for kind, chunk in split_into_text_and_tags(text):
        if kind != "tag":
            continue
        name, closing = read_tag_name(chunk)
        if name not in OK_TAGS:
            continue
        if not closing:
            open_tags.append(name)
            continue
        if not open_tags or open_tags[-1] != name:
            problems.append(f"сломан тег {chunk}")
            continue
        open_tags.pop()
    if open_tags:
        problems.append("незакрытые " + ",".join(open_tags))
    return problems
