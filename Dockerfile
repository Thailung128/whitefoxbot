FROM python:3.11-slim

# Ускоряем и делаем сборку предсказуемой
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала зависимости, потом код (кэш слоёв)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Теперь весь проект
COPY . /app

# Переменные окружения читаются Railway из Variables
# Запуск бота
CMD ["python", "-m", "app.bot"]
