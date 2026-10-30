from types import SimpleNamespace

import services.verify_python_code as v


class FakeCompletions:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        text = self.answers.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def fake_client(completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


async def test_empty_answer_is_retried_once(monkeypatch):
    completions = FakeCompletions(["", "<b>Панч</b>"])
    monkeypatch.setattr(v, "get_client", lambda: fake_client(completions))
    assert "Панч" in await v.ask_gpt("s", "u")
    assert completions.calls == 2


async def test_no_endless_retries(monkeypatch):
    completions = FakeCompletions(["", "", "лишнее"])
    monkeypatch.setattr(v, "get_client", lambda: fake_client(completions))
    assert await v.ask_gpt("s", "u") == ""
    assert completions.calls == 2
