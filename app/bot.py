import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

from .keyboards import MAIN_MENU, SPREADS_KB, preview_kb, final_kb
from .spreads import SPREAD_BY_ID
from .deck import draw_cards
from .utils import md_escape, render_cards_md, rounded_image_path
from .llm import build_interpretation

# ---- Инициализация окружения ----
load_dotenv()
TOKEN = os.getenv("TG_BOT_TOKEN")

# ---- Диспетчер ----
dp = Dispatcher()


# ---- Состояния ----
class Form(StatesGroup):
    waiting_question = State()
    chosen_spread = State()


# ---- Хендлеры ----
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Добро пожаловать в <b>White Fox</b> 🦊✨\n\nВыберите действие:",
        reply_markup=MAIN_MENU
    )


@dp.callback_query(F.data == "help")
async def on_help(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "Как это работает:\n"
        "1) Напишите ваш вопрос одним сообщением.\n"
        "2) Выберите расклад (кнопки 2×4).\n"
        "3) Посмотрите карты, интерпретации и итоговый ответ.",
        reply_markup=MAIN_MENU
    )
    await cb.answer()


@dp.callback_query(F.data == "about")
async def on_about(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "Колодa <b>White Fox</b> — минимализм и честные ответы. 🎴\n"
        "Мы делаем аккуратные колоды и честные расклады.",
        reply_markup=MAIN_MENU
    )
    await cb.answer()


@dp.callback_query(F.data == "ask")
async def on_ask(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_question)
    await cb.message.edit_text(
        "Сформулируйте ваш вопрос <b>одним сообщением</b> ✍️\n"
        "Например:\n"
        "• «Какой совет на ближайшую неделю?»\n"
        "• «Что важно понять про отношения?»\n"
        "• «В каком направлении двигаться в карьере?»"
    )
    await cb.answer()


@dp.message(Form.waiting_question)
async def on_question(msg: types.Message, state: FSMContext):
    question = (msg.text or "").strip()
    await state.update_data(question=question)
    await state.set_state(Form.chosen_spread)
    await msg.answer("Выберите расклад:", reply_markup=SPREADS_KB)


@dp.callback_query(F.data.startswith("spread:"), Form.chosen_spread)
async def on_spread(cb: types.CallbackQuery, state: FSMContext):
    _, spread_id = cb.data.split(":")
    spread = SPREAD_BY_ID[spread_id]
    await state.update_data(spread_id=spread_id)

    # Пробуем отправить схему расклада как изображение
    scheme_path = None
    for ext in ("png", "jpg", "jpeg"):
        p = os.path.join("media", "spreads", f"{spread_id}.{ext}")
        if os.path.exists(p):
            scheme_path = p
            break

    caption = f"<b>{spread.title}</b>\n\nПозиции: " + ", ".join(spread.positions)

    if scheme_path:
        try:
            await cb.message.answer_photo(
                FSInputFile(scheme_path),
                caption=caption + "\n\nВыберите действие:",
                reply_markup=preview_kb(spread_id),
            )
        except Exception:
            await cb.message.edit_text(
                caption + "\n\n(Схема недоступна, покажем текстовку)\n\nВыберите действие:",
                reply_markup=preview_kb(spread_id)
            )
    else:
        await cb.message.edit_text(
            caption + "\n\n(Схема будет добавлена позже)\n\nВыберите действие:",
            reply_markup=preview_kb(spread_id)
        )

    await cb.answer()


# ✅ Универсальный «Назад»: удаляем превью (фото/текст) и возвращаем список раскладов
@dp.callback_query(F.data == "back_to_spreads")
async def back_to_spreads(cb: types.CallbackQuery, state: FSMContext):
    """Удаляет и превью, и старое сообщение с выбором расклада."""
    await state.set_state(Form.chosen_spread)
    try:
        # Удаляем текущее сообщение (превью)
        await cb.message.delete()
        # Пытаемся удалить предыдущее сообщение (если есть)
        await cb.message.chat.delete_message(cb.message.message_id - 1)
    except Exception:
        pass
    # Отправляем новое одно сообщение "Выберите расклад"
    await cb.message.answer("Выберите расклад:", reply_markup=SPREADS_KB)
    await cb.answer()


# 🔁 Перетасовка → вытягивание → интерпретация → финал
@dp.callback_query(F.data.startswith("shuffle:"))
async def on_shuffle(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    spread_id = data.get("spread_id")
    question = data.get("question", "")
    if not spread_id:
        await cb.message.answer("Сначала выберите расклад.")
        await cb.answer()
        return

    spread = SPREAD_BY_ID[spread_id]

    await cb.message.answer("Колода перетасовывается… 🔁")

    k = len(spread.positions)
    drawn = draw_cards(k, reversed_enabled=True)

    pairs: list[dict] = []

    for pos_name, (card, is_rev) in zip(spread.positions, drawn):
        shown_name = card.name + (" (перевёрнутая)" if is_rev else "")

        # Для ИИ
        pairs.append({
            "position": pos_name,
            "name": card.name,
            "reversed": is_rev,
            "theses": getattr(card, "meanings", {"upright": "", "reversed": ""}),
        })

        caption = f"Карта открывается… ✨\n<b>{md_escape(pos_name)}</b> — {md_escape(shown_name)}"

        # Скругляем углы и отправляем как фото
        photo_path = None
        if card.image_path and os.path.exists(card.image_path):
            photo_path = rounded_image_path(card.image_path, radius=48) or card.image_path

        if photo_path and os.path.exists(photo_path):
            try:
                await cb.message.answer_photo(FSInputFile(photo_path), caption=caption)
            except Exception:
                await cb.message.answer(caption)
        else:
            await cb.message.answer(caption)

        await asyncio.sleep(0.15)

    # Подсказки позиций (hints)
    if getattr(spread, "hints", None) and len(spread.hints) == len(spread.positions):
        hints = spread.hints
    else:
        hints = [""] * len(spread.positions)

    # Интерпретация
    interp = await build_interpretation(
        question=question,
        spread_title=spread.title,
        pairs=pairs,
        position_hints=hints
    )

    cards_md = render_cards_md(interp.get("cards", []))
    summary = md_escape(interp.get("summary", ""))

    # Итог показываем везде, кроме "Путь (3 карты)" — id="path"
    show_summary = (spread.id != "path")

    final_text = f"<b>Ответ на ваш вопрос</b>\n\n{cards_md}"
    if show_summary:
        final_text += f"\n\n<b>Итог:</b> {summary}\n\n🌙 Благодарим за доверие. Белая Лисица рядом."

    await cb.message.answer(final_text, reply_markup=final_kb())
    await cb.answer()


# Финальные кнопки
@dp.callback_query(F.data == "new")
async def on_new(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Начнём заново. Выберите действие:", reply_markup=MAIN_MENU)
    await cb.answer()


# ---- Точка входа ----
async def main():
    if not TOKEN:
        raise RuntimeError("Нет TG_BOT_TOKEN в .env")
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
