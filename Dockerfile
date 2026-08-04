FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 importer \
    && mkdir -p /app/.cache \
    && chown -R importer:importer /app
USER importer

CMD ["sh", "-c", "python -m scripts.update_all_decks && python -m anki_actions.sync"]
