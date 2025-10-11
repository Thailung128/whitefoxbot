import os
from PIL import Image, ImageDraw

# ===== Настройки через .env (не обязательно) =====
# CARD_BG_PATH   = путь к фону, например: media/ui/card_bg.png
# CARD_SCALE     = масштаб карты поверх фона (0.9 = 90%)
# CARD_RADIUS    = радиус скругления (по умолчанию 48)
# ==================================================

def md_escape(s: str) -> str:
    """Простая экранизация для HTML/Telegram."""
    if s is None:
        return ""
    return s.replace("<", "&lt;").replace(">", "&gt;")

def render_cards_md(items: list[dict]) -> str:
    """Собирает блок с картами для финального сообщения."""
    lines = []
    for i, it in enumerate(items, 1):
        pos = it.get("position", "")
        name = it.get("name", "")
        meaning = it.get("meaning", "")
        lines.append(f"<b>{i}. {md_escape(pos)} — {md_escape(name)}</b>\n{md_escape(meaning)}")
    return "\n\n".join(lines)

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _env_float(name: str, default: float) -> float:
    try:
        v = float(os.getenv(name, "").strip() or default)
        return v
    except Exception:
        return default

def rounded_image_path(original_path: str, radius: int = None) -> str | None:
    """
    Готовит изображение карты для Telegram:
      1) Скругляет углы.
      2) Если задан фон — уменьшает карту и кладёт по центру на фоновую картинку.
      3) Сохраняет готовый PNG в кэш: media/cache/rounded/.
    Возвращает путь к готовому PNG или None (если не удалось).
    """
    if not original_path or not os.path.exists(original_path):
        return None

    # Параметры из .env
    bg_path = os.getenv("CARD_BG_PATH", "").strip() or os.path.join("media", "ui", "card_bg.png")
    scale = _env_float("CARD_SCALE", 0.90)  # уменьшение до 90%
    if radius is None:
        # можно переопределить радиус через .env
        radius = int(_env_float("CARD_RADIUS", 48))

    # Подготовка кэша
    cache_dir = os.path.join("media", "cache", "rounded")
    _ensure_dir(cache_dir)

    base_name = os.path.splitext(os.path.basename(original_path))[0]
    # учитываем в имени кэша радиус/scale и наличие фона
    suffix = f"_r{radius}_s{int(scale*100)}"
    has_bg = os.path.exists(bg_path)
    if has_bg:
        out_name = f"{base_name}{suffix}_bg.png"
    else:
        out_name = f"{base_name}{suffix}.png"
    out_path = os.path.join(cache_dir, out_name)

    # Если готовый PNG уже есть — возвращаем его
    if os.path.exists(out_path):
        return out_path

    try:
        with Image.open(original_path).convert("RGBA") as im:
            w, h = im.size

            # -------- 1) Скругляем углы исходной карты --------
            mask = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(mask)
            r = max(0, min(radius, min(w, h) // 2))
            draw.rounded_rectangle((0, 0, w, h), radius=r, fill=255)

            card_rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            card_rgba.paste(im, (0, 0), mask=mask)

            # Если нет фона — делаем аккуратную белую подложку как раньше (для фото)
            if not has_bg:
                bg = Image.new("RGB", (w, h), (255, 255, 255))
                bg.paste(card_rgba, mask=card_rgba.split()[3])  # по альфе
                bg.save(out_path, "PNG", optimize=True)
                return out_path

            # -------- 2) Есть фон: уменьшаем карту и кладём по центру --------
            try:
                with Image.open(bg_path) as bg_img:
                    # Приведём фон к размеру исходной карты, чтобы сохранить пропорции выдачи
                    bg_resized = bg_img.convert("RGB").resize((w, h), Image.LANCZOS)

                    # Масштабируем карту
                    scale = max(0.1, min(scale, 1.0))  # безопасный диапазон
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    card_small = card_rgba.resize((new_w, new_h), Image.LANCZOS)

                    # Центрируем
                    x = (w - new_w) // 2
                    y = (h - new_h) // 2

                    # Кладём карту на фон по альфе
                    bg_resized.paste(card_small, (x, y), card_small.split()[3])

                    # Сохраняем готовую композицию
                    bg_resized.save(out_path, "PNG", optimize=True)
                    return out_path
            except Exception:
                # если фон не удалось загрузить — fallback на белую подложку
                bg = Image.new("RGB", (w, h), (255, 255, 255))
                bg.paste(card_rgba, mask=card_rgba.split()[3])
                bg.save(out_path, "PNG", optimize=True)
                return out_path

    except Exception:
        return None
