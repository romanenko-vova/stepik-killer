import json

from db.database import on_startup
from db.module_crud import get_modules
from db.personal_crud import (
    create_personal_task,
    create_set,
    personal_counts,
    sets_for_user,
    tasks_with_status,
    user_can_open,
)
from db.seed import seed_if_empty
from db.users_crud import create_user, get_user
from db.zadacha_crud import (
    add_solution,
    get_attempt_count,
    get_progress,
    get_recent_attempts,
    get_stale_task_ids,
    get_task,
    get_tasks_by_topic,
    set_solution_review,
)
from db.admin_crud import list_students, student_solutions


async def test_seed_is_idempotent():
    await seed_if_empty()
    await seed_if_empty()
    modules = await get_modules()
    assert len(modules) == 4
    tasks = await get_tasks_by_topic("Первые заказы")
    assert len(tasks) == 6


async def test_create_user_twice_does_not_fail():
    first = await create_user(8500017318, "sasha", "Саша")
    second = await create_user(8500017318, "sasha", "Саша")
    assert first["id"] == second["id"]
    assert first["id_tg"] == 8500017318


async def test_solved_and_stale_follow_task_version():
    await seed_if_empty()
    user = await create_user(1)
    task = (await get_tasks_by_topic("Первые заказы"))[0]
    sid = await add_solution(user["id"], task["id"], "print(1)", "ok", [{"n": 1, "ok": True}])
    await set_solution_review(sid, "<b>норм</b>")

    solved, total, stale = await get_progress(user["id"])
    assert (solved, total, stale) == (1, 58, 0)

    # меняем подпись задачи — решение становится устаревшим
    from db.database import get_session
    from db.models import Task

    async with get_session() as session:
        db_task = await session.get(Task, task["id"])
        db_task.content_sig = "other"
        await session.commit()

    assert await get_stale_task_ids(user["id"]) == {task["id"]}
    assert (await get_progress(user["id"]))[0] == 0

    assert await get_attempt_count(user["id"], task["id"]) == 1
    recent = await get_recent_attempts(user["id"], task["id"])
    assert recent[0]["review"] == "<b>норм</b>"


async def test_personal_set_visible_only_to_owner():
    owner = await create_user(10)
    stranger = await create_user(11)
    set_id = await create_set(owner["id"], "Блок")
    task_id = await create_personal_task(set_id, "Задача", "Условие", [{"input": "1", "expected": "1"}], 1)
    task = await get_task(task_id)

    assert await user_can_open(owner["id"], task)
    assert not await user_can_open(stranger["id"], task)
    assert [s["title"] for s in await sets_for_user(owner["id"])] == ["Блок"]
    assert await personal_counts(owner["id"]) == (0, 1)

    await add_solution(owner["id"], task_id, "print(1)", "ok", [])
    assert await personal_counts(owner["id"]) == (1, 1)
    rows = await tasks_with_status(set_id, owner["id"])
    assert rows[0]["mark"] == "ok"


async def test_admin_lists_students_with_counts():
    await seed_if_empty()
    user = await create_user(20, None, "Петя")
    task = (await get_tasks_by_topic("Первые заказы"))[0]
    await add_solution(user["id"], task["id"], "x", "fail", [])
    await add_solution(user["id"], task["id"], "y", "ok", [])
    students = await list_students()
    me = next(s for s in students if s["id"] == user["id"])
    assert me["solved"] == 1
    assert me["attempts"] == 2
    assert me["name"] == "Петя"
    sols = await student_solutions(user["id"], task["id"])
    assert [s["code"] for s in sols] == ["y", "x"]


async def test_startup_creates_weekend_sets():
    await on_startup()
    alex = await get_user(8500017318)
    titles = [s["title"] for s in await sets_for_user(alex["id"])]
    assert len(titles) == 2
    assert json.loads((await get_task(1))["tests"])
