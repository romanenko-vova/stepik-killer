"""
Песочница гоняется в настоящем Docker. Без докера тесты пропускаются.
"""

import shutil
import subprocess

import pytest

from services.code_runner import run_tests

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None
    or subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="docker недоступен",
)

SUM_TESTS = [
    {"input": "2\n2", "expected": "4"},
    {"input": "10\n5", "expected": "15"},
    {"input": "-3\n3", "expected": "0"},
]


async def test_honest_solution_passes():
    ok, results = await run_tests("a = int(input())\nb = int(input())\nprint(a + b)", SUM_TESTS)
    assert ok
    assert all(r["ok"] for r in results)


async def test_wrong_answer_shows_diff():
    ok, results = await run_tests("a = input()\nb = input()\nprint(a + b)", SUM_TESTS)
    assert not ok
    assert results[0]["actual"] == "22"
    assert results[0]["expected"] == "4"


async def test_cannot_read_tests_from_container():
    cheat = (
        "import json, sys\n"
        "t = json.load(open('tests.json'))\n"
        "s = sys.stdin.read()\n"
        "print(next(x['expected'] for x in t if x['input'] == s))\n"
    )
    ok, results = await run_tests(cheat, SUM_TESTS)
    assert not ok
    assert "FileNotFoundError" in results[0]["error"]


async def test_infinite_loop_is_timeout():
    ok, results = await run_tests("while True:\n    pass", SUM_TESTS[:1])
    assert not ok
    assert results[0]["timeout"]


async def test_memory_hog_does_not_kill_runner():
    ok, results = await run_tests("x = [0] * (10 ** 9)\nprint(len(x))", SUM_TESTS[:1])
    assert not ok
    assert "MemoryError" in results[0]["error"]
    assert not results[0].get("infra")


async def test_fork_bomb_is_contained():
    bomb = "import os\nwhile True:\n    os.fork()\n"
    ok, results = await run_tests(bomb, SUM_TESTS[:1])
    assert not ok
    # либо упёрлись в лимит процессов, либо в таймаут — но не положили раннер
    assert results[0].get("timeout") or results[0].get("error")
    assert not results[0].get("infra")


async def test_output_flood_is_cut():
    ok, results = await run_tests("while True:\n    print('a' * 1000)", SUM_TESTS[:1])
    assert not ok
    assert results[0].get("timeout") or "много вывода" in results[0].get("error", "")


async def test_no_network():
    code = "import socket\nsocket.create_connection(('1.1.1.1', 80), timeout=2)\nprint('online')"
    ok, results = await run_tests(code, SUM_TESTS[:1])
    assert not ok
    assert "Error" in results[0]["error"]


async def test_solution_folder_is_read_only():
    code = "open('/code/solution.py', 'w').write('x')\nprint('written')"
    ok, results = await run_tests(code, SUM_TESTS[:1])
    assert not ok
    assert "Error" in results[0]["error"]
