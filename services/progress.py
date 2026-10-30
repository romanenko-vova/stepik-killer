"""Уровни по числу решённых задач. Пороги и названия — в config/funnel_texts.py."""

from config.funnel_texts import LEVELS, LEVEL_UP_TEXT, PROGRESS_NEXT_TEXT, PROGRESS_TEXT


def level_for(solved: int) -> tuple[int, str | None, int | None]:
    """(номер уровня с 1, название, сколько решённых нужно для следующего). 0 — ещё ни одного."""
    index, name = 0, None
    for i, (threshold, title) in enumerate(LEVELS, 1):
        if solved >= threshold:
            index, name = i, title
    next_threshold = LEVELS[index][0] if index < len(LEVELS) else None
    return index, name, next_threshold


def progress_text(solved_before: int, solved_now: int) -> str:
    before, _, _ = level_for(solved_before)
    index, name, next_threshold = level_for(solved_now)
    lines = []
    if index > before and name:
        lines.append(LEVEL_UP_TEXT.format(name=name))
    text = PROGRESS_TEXT.format(solved=solved_now, name=name or "—")
    if next_threshold is not None:
        text += PROGRESS_NEXT_TEXT.format(left=next_threshold - solved_now)
    lines.append(text)
    return "\n".join(lines)
