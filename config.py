import os
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_VISION_URL = os.getenv("YANDEX_VISION_URL")

SUPPORTED_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".jfif", ".webp", ".heic")