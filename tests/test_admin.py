import httpx

import admin.app as admin_app
from db.database import on_startup
from db.users_crud import get_user
from db.zadacha_crud import add_solution, set_solution_review


async def test_admin_pages_render(monkeypatch):
    monkeypatch.setattr(admin_app, "ADMIN_PASSWORD", "secret")
    await on_startup()
    alex = await get_user(8500017318)
    sid = await add_solution(alex["id"], 1, "print(1)", "ok", [{"n": 1, "ok": True}])
    await set_solution_review(sid, "<b>Принято</b>")

    transport = httpx.ASGITransport(app=admin_app.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", auth=("admin", "secret")) as client:
        for url in ("/", f"/u/{alex['id']}", f"/u/{alex['id']}/task/1", "/personal", "/personal/1"):
            response = await client.get(url)
            assert response.status_code == 200, url
        assert "Принято" in (await client.get(f"/u/{alex['id']}/task/1")).text

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/")).status_code == 401


async def test_funnel_page_counts_sources(monkeypatch):
    from db.funnel_crud import funnel_by_day, funnel_by_source
    from db.users_crud import create_user
    from db.zadacha_crud import add_solution, next_task_for
    from services.events import track

    monkeypatch.setattr(admin_app, "ADMIN_PASSWORD", "secret")
    await on_startup()
    for tg, source in ((9001, "reel_1"), (9002, "reel_1"), (9003, None)):
        user = await create_user(tg, None, None, 3, source)
        task = await next_task_for(user["id"])
        if tg != 9003:
            await add_solution(user["id"], task["id"], "ok", "ok", [])
            await track(user["id"], "solved", {})
    await track((await get_user(9001))["id"], "trial_click", None)

    rows = {r["source"]: r for r in await funnel_by_source(30)}
    assert rows["reel_1"]["starts"] == 2
    assert rows["reel_1"]["solved_1"] == 2
    assert rows["reel_1"]["trial_click"] == 1
    assert rows["—"]["starts"] == 1
    assert "Александр" not in str(rows)  # ученики не в воронке
    today = (await funnel_by_day(14))[0]
    assert today["starts"] >= 3 and today["solved"] == 2

    transport = httpx.ASGITransport(app=admin_app.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", auth=("admin", "secret")) as client:
        response = await client.get("/funnel")
        assert response.status_code == 200
        assert "reel_1" in response.text
