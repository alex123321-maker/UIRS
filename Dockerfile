FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "8000"]
