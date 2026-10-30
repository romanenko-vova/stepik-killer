import json
from collections import Counter
from pathlib import Path

from scripts.check_catalog import check, iter_tasks

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "db" / "catalog.json").read_text(encoding="utf-8"))
STARTER = json.loads((ROOT / "db" / "starter.json").read_text(encoding="utf-8"))

# без ввода по замыслу: упражнение на готовый словарь
NO_INPUT = {"03-03-06"}


def test_reference_solutions_pass_every_test():
    assert check(CATALOG) == []


def test_every_task_has_enough_tests():
    for key, _topic, task in iter_tasks(CATALOG):
        if key in NO_INPUT:
            continue
        assert len(task["tests"]) >= 5, f"{key} {task['title']}"
    assert all(len(t["tests"]) >= 6 for t in STARTER)


def test_keys_and_titles_are_unique():
    keys = [key for key, _t, _q in iter_tasks(CATALOG)]
    assert len(keys) == len(set(keys))
    titles = Counter(q["title"] for _k, _t, q in iter_tasks(CATALOG))
    titles.update(t["title"] for t in STARTER)
    assert [t for t, n in titles.items() if n > 1] == []


def test_warmups_go_first():
    for module in CATALOG:
        for topic in module["topics"]:
            seen_regular = False
            for task in topic["tasks"]:
                if task["title"].startswith("Разгон"):
                    assert not seen_regular, topic["title"]
                else:
                    seen_regular = True
