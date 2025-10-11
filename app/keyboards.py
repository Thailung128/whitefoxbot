from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---- Главное меню ----
MAIN_MENU = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Задать вопрос", callback_data="ask")],
        [
            InlineKeyboardButton(
                text="🛍️ Каталог колод",
                url="https://www.ozon.ru/seller/white-fox-2587631/?miniapp=seller_2587631"
            )
        ],
        [
            InlineKeyboardButton(
                text="🦊 О White Fox",
                url="https://t.me/whitefoxtarot"
            )
        ],
    ]
)

# ---- Клавиатура с раскладами ----
SPREADS_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Путь (3)", callback_data="spread:path"),
            InlineKeyboardButton(text="3 карты", callback_data="spread:three"),
        ],
        [
            InlineKeyboardButton(text="Крест выбора", callback_data="spread:choice_cross"),
            InlineKeyboardButton(text="Отношения", callback_data="spread:love"),
        ],
        [
            InlineKeyboardButton(text="Пирамида успеха", callback_data="spread:success_pyramid"),
            InlineKeyboardButton(text="Подкова", callback_data="spread:horseshoe"),
        ],
        [
            InlineKeyboardButton(text="Дерево жизни", callback_data="spread:tree_of_life"),
            InlineKeyboardButton(text="Кельтский крест", callback_data="spread:celtic"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"),
        ],
    ]
)

# ---- Предпросмотр расклада ----
def preview_kb(spread_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎴 Сделать расклад", callback_data=f"shuffle:{spread_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_spreads")],
        ]
    )

# ---- Финальное сообщение ----
def final_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Новый расклад", callback_data="new")],
        ]
    )
