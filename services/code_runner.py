import asyncio
import json
import tempfile
from pathlib import Path

# на сервере несколько человек могут жать «проверить» сразу —
# без очереди docker плодит контейнеры и честные тесты падают по таймауту
docker_lock = asyncio.Lock()

# крутится уже внутри контейнера: solution.py рядом, тесты в tests.json
RUNNER = r"""
import json
import subprocess
import sys

tests = json.load(open("tests.json", encoding="utf-8"))
results = []

for i, test in enumerate(tests, 1):
    try:
        proc = subprocess.run(
            [sys.executable, "solution.py"],
            input=test["input"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        results.append({"n": i, "ok": False, "timeout": True})
        continue

    if proc.returncode != 0:
        results.append({"n": i, "ok": False, "error": proc.stderr[-500:]})
        continue

    actual = proc.stdout.strip()
    expected = test["expected"].strip()
    if actual == expected:
        results.append({"n": i, "ok": True})
    else:
        results.append(
            {
                "n": i,
                "ok": False,
                "input": test["input"],
                "expected": expected,
                "actual": actual,
            }
        )

print(json.dumps(results, ensure_ascii=False))
"""


async def run_tests(code: str, tests: list) -> tuple[bool, list]:
    async with docker_lock:
        return await _run_tests_in_docker(code, tests)


async def _run_tests_in_docker(code: str, tests: list) -> tuple[bool, list]:
    # один docker run на все тесты — иначе каждый тест ждёт старт контейнера
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "solution.py").write_text(code, encoding="utf-8")
        (folder / "tests.json").write_text(
            json.dumps(tests, ensure_ascii=False),
            encoding="utf-8",
        )
        (folder / "run_all.py").write_text(RUNNER, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{tmp}:/code",
            "-w",
            "/code",
            "python:3.12-slim",
            "python",
            "run_all.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=40)
        except asyncio.TimeoutError:
            proc.kill()
            return False, [{"n": i, "ok": False, "timeout": True} for i in range(1, len(tests) + 1)]

        if proc.returncode != 0:
            err = stderr.decode()[-500:]
            return False, [{"n": 1, "ok": False, "error": err or "контейнер упал"}]

        results = json.loads(stdout.decode())
        all_ok = all(item.get("ok") for item in results)
        return all_ok, results
