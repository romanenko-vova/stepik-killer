"""
Перенос данных бота из SQLite в Postgres.

    alembic upgrade head                                   # схема должна уже быть
    python -m scripts.migrate_sqlite_to_pg path/to/stepik_killer.db [--report MIGRATION_REPORT.md]

Что делает:
- читает все таблицы SQLite, какие колонки есть (старые базы без set_id/pos тоже годятся);
- пишет в Postgres через модели с теми же id: INSERT ... ON CONFLICT (id) DO UPDATE.
  Повторный запуск ничего не дублирует, а дотягивает изменения — можно гонять сколько угодно;
- строки с битыми ссылками (решение на удалённую задачу и т.п.) SQLite молча хранил,
  а Postgres с внешними ключами не примет. Их не теряем: кладём в <отчёт>.orphans.json и считаем отдельно;
- двигает счётчики id, чтобы новые записи не столкнулись со старыми;
- в конце сверяет каждую таблицу: число строк и хеш содержимого по общим колонкам.
  Код выхода 0 только если всё сошлось.
"""

import argparse
import asyncio
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402

from db.database import engine, get_session  # noqa: E402
from db.models import (  # noqa: E402
    CatalogMeta,
    Module,
    PersonalSet,
    PersonalSetAccess,
    Solution,
    Task,
    Topic,
    User,
)

# порядок важен: сначала те, на кого ссылаются
TABLES = [User, Module, Topic, PersonalSet, PersonalSetAccess, Task, CatalogMeta, Solution]

# внешние ключи: колонка -> (таблица, обязательна ли ссылка)
FOREIGN = {
    "topics": {"module_id": ("modules", False)},
    "personal_sets": {"user_id": ("users", True)},
    "personal_set_access": {"set_id": ("personal_sets", True), "user_id": ("users", True)},
    "tasks": {"set_id": ("personal_sets", False)},
    "solutions": {"user_id": ("users", True), "task_id": ("tasks", True)},
}

BATCH = 500


def parse_dt(value):
    # SQLite CURRENT_TIMESTAMP — строка 'YYYY-MM-DD HH:MM:SS' в UTC
    if value is None or isinstance(value, datetime):
        return value
    raw = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:26], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"не понял дату: {value!r}")


def pk_columns(model) -> list[str]:
    return [col.name for col in model.__table__.primary_key.columns]


def model_columns(model) -> dict:
    return {col.name: col for col in model.__table__.columns}


def read_sqlite(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[dict]]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    if not exists:
        return [], []
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    order = "id" if "id" in cols else ", ".join(cols)
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY {order}")]
    return cols, rows


def normalize(model, row: dict, shared: list[str]) -> dict:
    cols = model_columns(model)
    out = {}
    for name in shared:
        value = row.get(name)
        col = cols[name]
        if name == "created_at":
            value = parse_dt(value)
            if value is None:
                continue  # пусть Postgres поставит now()
        if name == "toxic_level" and value is None:
            value = 0
        if name == "status" and value is None:
            value = "new"
        if value is not None and col.type.python_type is int and not isinstance(value, int):
            value = int(value)
        out[name] = value
    return out


def row_fingerprint(row: dict, names: list[str]) -> str:
    parts = []
    for name in names:
        value = row.get(name)
        if isinstance(value, datetime):
            value = value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        elif name == "created_at" and value is not None:
            value = parse_dt(value).strftime("%Y-%m-%d %H:%M:%S")
        elif name == "toxic_level" and value is None:
            value = 0
        parts.append("" if value is None else str(value))
    return "\x1f".join(parts)


def table_hash(rows: list[dict], names: list[str], key: list[str]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda r: tuple(r[k] for k in key)):
        digest.update(row_fingerprint(row, names).encode("utf-8"))
        digest.update(b"\x1e")
    return digest.hexdigest()


async def upsert(model, rows: list[dict]):
    if not rows:
        return
    key = pk_columns(model)
    async with get_session() as session:
        for start in range(0, len(rows), BATCH):
            chunk = rows[start : start + BATCH]
            # по строке: колонки у строк могут отличаться (created_at=None не пишем)
            for row in chunk:
                stmt = insert(model).values(**row)
                update_cols = {c: stmt.excluded[c] for c in row if c not in key}
                if update_cols:
                    stmt = stmt.on_conflict_do_update(index_elements=key, set_=update_cols)
                else:
                    stmt = stmt.on_conflict_do_nothing(index_elements=key)
                await session.execute(stmt)
        await session.commit()


async def reset_sequences(source_max: dict[str, int]):
    # от максимума в источнике, включая битые строки: их id не отдаём новым записям
    async with engine.begin() as conn:
        for model in TABLES:
            if "id" not in model_columns(model) or model is CatalogMeta:
                continue
            table = model.__tablename__
            await conn.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"GREATEST(COALESCE((SELECT MAX(id) FROM {table}), 0), :src) + 1, false)"
                ),
                {"src": source_max.get(table, 0)},
            )


async def pg_rows(model, names: list[str]) -> list[dict]:
    cols = [getattr(model, n) for n in names]
    async with get_session() as session:
        result = await session.execute(select(*cols))
        return [dict(r._mapping) for r in result]


async def check_schema():
    async with engine.connect() as conn:
        found = await conn.execute(text("SELECT to_regclass('public.alembic_version')"))
        if found.scalar() is None:
            raise SystemExit("В Postgres нет схемы. Сначала: alembic upgrade head")


async def migrate(sqlite_path: Path, report_path: Path, force: bool = False) -> bool:
    await check_schema()
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # что уже признано валидным — для проверки ссылок
    valid_ids: dict[str, set] = {}
    orphans: dict[str, list] = {}
    stats = []

    for model in TABLES:
        table = model.__tablename__
        src_cols, src_rows = read_sqlite(conn, table)
        shared = [c for c in model_columns(model) if c in src_cols]
        missing_in_src = [c for c in model_columns(model) if c not in src_cols]
        dropped_src = [c for c in src_cols if c not in model_columns(model)]

        good, bad = [], []
        for row in src_rows:
            broken = []
            for col, (ref, required) in FOREIGN.get(table, {}).items():
                value = row.get(col)
                if value is None:
                    if required:
                        broken.append(f"{col}=NULL")
                    continue
                if int(value) not in valid_ids.get(ref, set()):
                    broken.append(f"{col}={value} нет в {ref}")
            if broken:
                bad.append({"row": row, "why": broken})
            else:
                good.append(row)

        if "id" in src_cols:
            valid_ids[table] = {int(r["id"]) for r in good}
        if bad:
            orphans[table] = bad

        stats.append(
            {
                "table": table,
                "source": len(src_rows),
                "written": len(good),
                "orphans": len(bad),
                "shared": shared,
                "missing_in_src": missing_in_src,
                "dropped_src": dropped_src,
                "src_good": good,
                "src_rows": src_rows,
            }
        )

    conn.close()

    # в Postgres не должно быть чужих строк: иначе id и cat_key столкнутся с источником
    foreign_rows = []
    for item in stats:
        model = next(m for m in TABLES if m.__tablename__ == item["table"])
        key = pk_columns(model)
        src_keys = {tuple(r[k] for k in key) for r in item["src_good"]}
        target = await pg_rows(model, key)
        extra = [r for r in target if tuple(r[k] for k in key) not in src_keys]
        if extra:
            foreign_rows.append(f"{item['table']}: {len(extra)}")
    if foreign_rows and not force:
        raise SystemExit(
            "В Postgres уже есть строки, которых нет в SQLite: "
            + ", ".join(foreign_rows)
            + ".\nМигрировать нужно в пустую базу (бот на ней ещё не запускался). "
            "Пересоздай базу или запусти с --force, если понимаешь, что делаешь."
        )

    for item in stats:
        model = next(m for m in TABLES if m.__tablename__ == item["table"])
        await upsert(model, [normalize(model, r, item["shared"]) for r in item["src_good"]])
    await reset_sequences(
        {
            item["table"]: max((int(r["id"]) for r in item["src_rows"] if r.get("id") is not None), default=0)
            for item in stats
        }
    )

    # сверка
    all_ok = True
    for item in stats:
        model = next(m for m in TABLES if m.__tablename__ == item["table"])
        key = pk_columns(model)
        names = item["shared"]
        target = await pg_rows(model, names) if names else []
        src_keys = {tuple(r[k] for k in key) for r in item["src_good"]}
        target_same = [r for r in target if tuple(r[k] for k in key) in src_keys]
        item["target"] = len(target)
        item["extra_in_target"] = len(target) - len(target_same)
        item["count_ok"] = len(target_same) == item["written"]
        item["hash_ok"] = table_hash(item["src_good"], names, key) == table_hash(target_same, names, key)
        item["ok"] = item["count_ok"] and item["hash_ok"] and item["source"] == item["written"] + item["orphans"]
        all_ok = all_ok and item["ok"]

    orphans_path = report_path.with_suffix(".orphans.json")
    if orphans:
        orphans_path.write_text(json.dumps(orphans, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        f"Источник: `{sqlite_path.name}`, {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        "",
        "| Таблица | В SQLite | Перенесено | Битые ссылки | В Postgres | Лишних в PG | Число | Содержимое |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in stats:
        lines.append(
            f"| {item['table']} | {item['source']} | {item['written']} | {item['orphans']} | "
            f"{item['target']} | {item['extra_in_target']} | {'✓' if item['count_ok'] else '✗'} | "
            f"{'✓' if item['hash_ok'] else '✗'} |"
        )
    lines.append("")
    for item in stats:
        if item["source"] == 0 and not item["shared"]:
            lines.append(f"- `{item['table']}`: в SQLite такой таблицы не было.")
            continue
        if item["missing_in_src"] or item["dropped_src"]:
            lines.append(
                f"- `{item['table']}`: в SQLite не было колонок {item['missing_in_src'] or '—'}"
                f" (стоят значения по умолчанию); в Postgres нет колонок {item['dropped_src'] or '—'}."
            )
    if orphans:
        lines.append(f"- Строки с битыми ссылками сохранены в `{orphans_path.name}`, в Postgres не записаны.")
    lines.append("")
    lines.append("Итог: **всё сошлось**." if all_ok else "Итог: **есть расхождения**, смотри ✗.")
    report = "\n".join(lines)
    report_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    return all_ok


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite")
    parser.add_argument("--report", default="MIGRATION_REPORT.md")
    parser.add_argument("--force", action="store_true", help="писать даже если в Postgres есть чужие строки")
    args = parser.parse_args()
    ok = await migrate(Path(args.sqlite), Path(args.report), args.force)
    await engine.dispose()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
