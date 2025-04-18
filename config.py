import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токены доступа
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
YANDEX_GPT_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_GPT_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
MASCOT_SVG_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "assets", "mascot-template.svg")

# Настройка параметров для модели
GPT_MODEL_PARAMS = {
    "temperature": 0.6,
    "max_tokens": 1500
}

def configure_logging():
    """Настройка логирования"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )