from openai import AsyncOpenAI


async def verify_python_code(code: str, condition: str):
    client = AsyncOpenAI()
    prompt = f"""
УСЛОВИЕ:
{condition}

КОД:
{code}
Верно ли он работает? Ответь коротко (Да/Нет) и объясни почему.
"""
    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=[{"role": "user", "content": prompt}],
    )

    result_text = response.output_text

    if result_text.startswith("Да"):
        return True, result_text

    return False, result_text
