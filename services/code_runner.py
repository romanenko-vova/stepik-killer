import asyncio
import tempfile
from pathlib import Path


async def run_fake_test(code: str) -> tuple[bool, str]:
    # один захардкоженный тест — потом можно будет брать из БД
    test_input = "2\n3\n"
    expected = "5"

    # пишем код ученика во временный файл
    with tempfile.TemporaryDirectory() as tmp:
        solution = Path(tmp) / "solution.py"
        solution.write_text(code, encoding="utf-8")

        # запускаем этот файл внутри docker
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
            return False, "Тест 1: ❌ слишком долго (больше 10 секунд)"

        if proc.returncode != 0:
            return False, f"Тест 1: ❌ ошибка\n{stderr.decode()[-500:]}"

        actual = stdout.decode().strip()

        if actual == expected:
            return True, (
                f"Тест 1: ✅\n"
                f"Вход: {test_input!r}\n"
                f"Ожидалось: {expected!r}\n"
                f"Получено: {actual!r}"
            )

        return False, (
            f"Тест 1: ❌\n"
            f"Вход: {test_input!r}\n"
            f"Ожидалось: {expected!r}\n"
            f"Получено: {actual!r}"
        )
