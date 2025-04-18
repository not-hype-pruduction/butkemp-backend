FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для Cairo
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]