"""
Запуск решения ученика на тестах в одноразовом Docker-контейнере.

Как устроено:
- в контейнер монтируется только папка с solution.py и run_all.py, read-only;
- тесты раннер получает через stdin и держит в памяти — в файловой системе
  контейнера их нет, прочитать ожидаемый вывод из решения нельзя;
- контейнер без сети, без прав, с лимитами памяти, процессов и CPU;
- каждый тест — отдельный процесс с лимитом времени и размера вывода.
"""

import asyncio
import json
import logging
import os
import stat
import tempfile
from pathlib import Path

from config.config import DOCKER_IMAGE, DOCKER_PARALLEL

logger = logging.getLogger(__name__)

# параллельно крутим несколько контейнеров, но не бесконечно:
# иначе наплыв после ролика положит сервер
docker_slots = asyncio.Semaphore(DOCKER_PARALLEL)

TEST_TIMEOUT = 5  # секунд на один тест
OUTPUT_LIMIT = 200_000  # байт вывода, дальше режем
SOLUTION_MEMORY = 192 * 1024 * 1024  # лимит адресного пространства на решение

# крутится внутри контейнера. Тесты приходят в stdin одной JSON-строкой,
# решение лежит рядом в solution.py (read-only)
RUNNER = r"""
import json
import resource
import subprocess
import sys

cfg = json.loads(sys.stdin.readline())
tests = cfg["tests"]
timeout = cfg["timeout"]
out_limit = cfg["out_limit"]
mem_limit = cfg["mem_limit"]


def limits():
    # размер файла = размер stdout, пишем его в файл; память — чтобы один
    # список на миллиард не ронял весь контейнер
    resource.setrlimit(resource.RLIMIT_FSIZE, (out_limit, out_limit))
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))


results = []
for i, test in enumerate(tests, 1):
    out_path = f"/tmp/out_{i}.txt"
    err_path = f"/tmp/err_{i}.txt"
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "solution.py"],
                input=test["input"].encode("utf-8"),
                stdout=out,
                stderr=err,
                timeout=timeout,
                preexec_fn=limits,
            )
        except subprocess.TimeoutExpired:
            results.append({"n": i, "ok": False, "timeout": True})
            continue

    actual = open(out_path, encoding="utf-8", errors="replace").read()
    stderr = open(err_path, encoding="utf-8", errors="replace").read()

    if proc.returncode != 0:
        if "File too large" in stderr or (proc.returncode < 0 and len(actual) >= out_limit - 1):
            stderr = "Слишком много вывода — программа печатает без остановки."
        elif "MemoryError" in stderr:
            stderr = "MemoryError: программа съела всю память."
        results.append({"n": i, "ok": False, "error": stderr[-500:]})
        continue

    actual = actual.strip()
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
                "actual": actual[:2000],
            }
        )

print(json.dumps(results, ensure_ascii=False))
"""


def infra_error(tests: list, reason: str) -> list[dict]:
    # проверка не состоялась по нашей вине — ученику это надо показать отдельно
    logger.error("песочница не отработала: %s", reason)
    return [{"n": 1, "ok": False, "error": reason, "infra": True}]


def total_timeout(tests: list) -> int:
    # старт контейнера + по тесту с запасом, но не бесконечно
    return min(120, 15 + (TEST_TIMEOUT + 1) * len(tests))


async def run_tests(code: str, tests: list) -> tuple[bool, list]:
    async with docker_slots:
        return await _run_tests_in_docker(code, tests)


def _prepare_folder(folder: Path, code: str):
    # контейнер работает от nobody, папка от tempfile создаётся 0700 — открываем на чтение
    (folder / "solution.py").write_text(code, encoding="utf-8")
    (folder / "run_all.py").write_text(RUNNER, encoding="utf-8")
    os.chmod(folder, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    for name in ("solution.py", "run_all.py"):
        os.chmod(folder / name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def docker_command(folder: Path) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--memory",
        "256m",
        "--memory-swap",
        "256m",
        "--cpus",
        "1",
        "--pids-limit",
        "64",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,size=32m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "65534:65534",
        "-e",
        "HOME=/tmp",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-v",
        f"{folder}:/code:ro",
        "-w",
        "/code",
        DOCKER_IMAGE,
        "python",
        "run_all.py",
    ]


async def _run_tests_in_docker(code: str, tests: list) -> tuple[bool, list]:
    payload = json.dumps(
        {
            "tests": tests,
            "timeout": TEST_TIMEOUT,
            "out_limit": OUTPUT_LIMIT,
            "mem_limit": SOLUTION_MEMORY,
        },
        ensure_ascii=False,
    )

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _prepare_folder(folder, code)

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_command(folder),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return False, infra_error(tests, "docker не найден")

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate((payload + "\n").encode("utf-8")),
                timeout=total_timeout(tests),
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return False, [
                {"n": i, "ok": False, "timeout": True} for i in range(1, len(tests) + 1)
            ]

    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[-500:]
        return False, infra_error(tests, err or f"контейнер завершился с кодом {proc.returncode}")

    try:
        results = json.loads(stdout.decode())
    except json.JSONDecodeError:
        return False, infra_error(tests, "раннер вернул не JSON: " + stdout.decode(errors="replace")[-300:])

    all_ok = bool(results) and all(item.get("ok") for item in results)
    return all_ok, results
