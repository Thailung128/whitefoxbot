import os
import json
from typing import Any
import httpx
from dotenv import load_dotenv

# Загружаем .env сразу при импорте
load_dotenv()

SYSTEM_PROMPT = (
    "Ты — профессиональный таролог студии White Fox. Твоя задача — давать глубокие, но лаконичные "
    "интерпретации карт Таро в контексте конкретного вопроса и позиции в раскладе.\n\n"
    "Стиль: умный, спокойный, честный, без мистики. Пиши как внимательный собеседник, а не прорицатель.\n\n"
    "Для каждой карты опирайся на:\n"
    "- её название, положение (прямое или перевёрнутое), и тезисы (если есть),\n"
    "- значение позиции в раскладе (например, «Прошлое», «Совет», «Что мешает» и т.п.),\n"
    "- общий вопрос пользователя.\n\n"
    "Формат ответа — только JSON:\n"
    "{ 'cards': [ { 'position': '...', 'name': '...', 'meaning': '... (3–5 предложений, контекстно, по позиции)' } ],"
    "  'summary': '... (3–6 предложений — общий ответ, синтезируя все карты)' }\n\n"
    "Не используй эзотерических клише, не повторяй одно и то же. Пиши осмысленно и естественно."
)


def _strip_code_fences(text: str) -> str:
    """Удаляем обёртку ```json ... ``` если модель так ответила."""
    t = text.strip()
    if t.startswith("```") and t.endswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json\n"):
            t = t[5:]
    return t

async def build_interpretation(
    question: str,
    spread_title: str,
    pairs: list[Any],
    position_hints: list[str] | None = None,
) -> dict[str, Any]:
    """
    pairs — список словарей: {"position","name","reversed","theses":{upright,reversed}} (или старый формат кортежей)
    """

    # Читаем ключ и модель при каждом вызове
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    # 1️⃣ Без ключа — демо
    if not OPENAI_API_KEY:
        return {
            "cards": [
                {
                    "position": (item.get("position") if isinstance(item, dict) else item[0]),
                    "name": (
                        (item.get("name") if isinstance(item, dict) else item[1])
                        + (" (перев.)" if (item.get("reversed") if isinstance(item, dict) else item[2]) else "")
                    ),
                    "meaning": "Краткое значение карты (демо). Подключите OPENAI_API_KEY для настоящего вывода.",
                }
                for item in pairs
            ],
            "summary": "Итоговый ответ (демо).",
        }

    # 2️⃣ Готовим payload карт
    cards_payload = []
    for item in pairs:
        if isinstance(item, dict):
            cards_payload.append(item)
        else:
            position, name, reversed_flag = item
            cards_payload.append({"position": position, "name": name, "reversed": reversed_flag})

    # Добавим подсказки к позициям
    if position_hints and len(position_hints) == len(cards_payload):
        for i, hint in enumerate(position_hints):
            cards_payload[i]["hint"] = hint

    user_payload = {
        "question": question,
        "spread_title": spread_title,
        "cards": cards_payload,
        "format_requirements": {
            "type": "json",
            "schema": {
                "cards": [{"position": "string", "name": "string", "meaning": "string"}],
                "summary": "string (3–6 предложений, связный ответ на вопрос пользователя)",
            },
            "notes": [
                "Строго учитывай позицию и перевёрнутость.",
                "Используй theses, если они есть.",
                "Если hint присутствует — учти его.",
                "Пиши кратко и по делу, без эзотерических терминов.",
                "Верни только JSON, без текста вокруг.",
            ],
        },
    }

    prompt = (
        "Сгенерируй толкование расклада Таро в формате JSON по схеме выше.\n"
        "Важно: не добавляй лишнего текста — только JSON.\n"
        f"Данные: {json.dumps(user_payload, ensure_ascii=False)}"
    )

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 900,
    }

    # 3️⃣ Запрос к OpenAI
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
            )
            res.raise_for_status()
            data = res.json()
            text = data["choices"][0]["message"]["content"]
    except Exception as e:
        return {"cards": [], "summary": f"Не удалось получить ответ от модели: {e}"}

    # 4️⃣ Парсим JSON
    t = _strip_code_fences(text)
    try:
        parsed = json.loads(t)
        if "cards" in parsed and "summary" in parsed and isinstance(parsed["cards"], list):
            return parsed
        return {"cards": [], "summary": t[:1500]}
    except Exception:
        return {"cards": [], "summary": t[:1500]}
