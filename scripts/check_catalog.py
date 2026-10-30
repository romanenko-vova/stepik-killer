"""
Проверка каталога эталонными решениями.

    python -m scripts.check_catalog            # эталоны против всех тестов
    python -m scripts.check_catalog --fill     # + дописать тесты из EXTRA в db/catalog.json

Решения запускаются на хосте через `python -I` — это наш код, песочница не нужна.
Новый тест дописывается, только если эталон прошёл все старые тесты задачи.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.catalog_refs import EXTRA, REFS  # noqa: E402

CATALOG = ROOT / "db" / "catalog.json"


def task_key(mi: int, ti: int, qi: int, task: dict) -> str:
    # явный ключ, если задачу переставили; иначе по месту — как в db/seed.py
    return task.get("key") or f"{mi:02d}-{ti:02d}-{qi:02d}"


def iter_tasks(catalog: list):
    for mi, module in enumerate(catalog, 1):
        for ti, topic in enumerate(module["topics"], 1):
            for qi, task in enumerate(topic["tasks"], 1):
                yield task_key(mi, ti, qi, task), topic, task


def run(code: str, stdin: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-I", "-c", code],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "упало"
    return True, proc.stdout.strip()


def check(catalog: list) -> list[str]:
    problems = []
    for key, _topic, task in iter_tasks(catalog):
        code = REFS.get(key)
        if code is None:
            problems.append(f"{key} «{task['title']}»: нет эталона")
            continue
        for n, test in enumerate(task["tests"], 1):
            ok, out = run(code, test["input"])
            if not ok or out != test["expected"].strip():
                problems.append(
                    f"{key} «{task['title']}» тест {n}: ввод {test['input']!r}, "
                    f"ждали {test['expected']!r}, эталон {out!r}"
                )
    return problems


def fill(catalog: list) -> int:
    added = 0
    for key, _topic, task in iter_tasks(catalog):
        inputs = {t["input"] for t in task["tests"]}
        for stdin in EXTRA.get(key, []):
            if stdin in inputs:
                continue
            ok, out = run(REFS[key], stdin)
            if not ok:
                raise SystemExit(f"{key}: эталон упал на новом вводе {stdin!r}: {out}")
            task["tests"].append({"input": stdin, "expected": out})
            inputs.add(stdin)
            added += 1
    return added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fill", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    problems = check(catalog)
    if problems:
        print("\n".join(problems))
        raise SystemExit(1)
    print("Эталоны прошли все тесты.")

    if args.fill:
        added = fill(catalog)
        CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Добавлено тестов: {added}")
        problems = check(catalog)
        if problems:
            print("\n".join(problems))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
