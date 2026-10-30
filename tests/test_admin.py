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
