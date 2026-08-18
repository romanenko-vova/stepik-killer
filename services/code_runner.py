import asyncio
import tempfile
from pathlib import Path


async def run_tests(code: str, tests: list) -> tuple[bool, list]:
    # пишем код ученика во временный файл и гоняем каждый тест в docker
    all_ok = True
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        solution = Path(tmp) / "solution.py"
        solution.write_text(code, encoding="utf-8")

        for i, test in enumerate(tests, 1):
            test_input = test["input"]
            expected = test["expected"].strip()

            proc = await asyncio.create_subprocess_exec(
                "docker",
                "run",
                "--rm",
                "-i",
                "--network",
                "none",
                "-v",
                f"{tmp}:/code",
                "-w",
                "/code",
                "python:3.12-slim",
                "python",
                "solution.py",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(test_input.encode()),
                    timeout=10,
                )
            except asyncio.TimeoutError:
                proc.kill()
                all_ok = False
                results.append({"n": i, "ok": False, "timeout": True})
                continue

            if proc.returncode != 0:
                all_ok = False
                err = stderr.decode()[-500:]
                results.append({"n": i, "ok": False, "error": err})
                continue

            actual = stdout.decode().strip()
            if actual == expected:
                results.append({"n": i, "ok": True})
            else:
                all_ok = False
                results.append(
                    {
                        "n": i,
                        "ok": False,
                        "input": test_input,
                        "expected": expected,
                        "actual": actual,
                    }
                )

    return all_ok, results
