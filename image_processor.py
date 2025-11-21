import os
import cv2
import numpy as np
from PIL import Image


def enhance_image_quality(image_path):
    """Улучшает качество изображения для лучшего распознавания"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)

        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        gray = cv2.filter2D(gray, -1, kernel)
        gray = cv2.convertScaleAbs(gray, alpha=1.3, beta=0)

        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        enhanced_path = image_path + "_enhanced.jpg"
        cv2.imwrite(enhanced_path, gray)
        print("Качество изображения улучшено")
        return enhanced_path

    except Exception as e:
        print(f"Ошибка улучшения качества: {e}")
        return image_path


def convert_heic_to_jpg(image_path):
    """Конвертирует HEIC в JPG используя pillow-heif"""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()

        with Image.open(image_path) as img:
            temp_path = image_path.replace(".heic", "_converted.jpg").replace(".HEIC", "_converted.jpg")
            img.convert("RGB").save(temp_path, "JPEG", quality=85)
            print(f"HEIC сконвертирован в JPG: {temp_path}")
            return temp_path
    except ImportError:
        return None
    except Exception as e:
        print(f"Ошибка конвертации HEIC: {e}")
        return None


def compress_image_for_api(image_path, max_size_mb=1):
    """Сжимает изображение для API"""
    try:
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size <= max_size_mb:
            return image_path

        print(f"Сжимаем: {file_size:.1f}MB -> {max_size_mb}MB")

        with Image.open(image_path) as img:
            width, height = img.size
            if width > 2000 or height > 2000:
                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)

            temp_path = image_path + "_compressed.jpg"
            img.convert("RGB").save(temp_path, "JPEG", quality=70, optimize=True)
            return temp_path

    except Exception as e:
        print(f"Ошибка сжатия: {e}")
        return image_path


def prepare_image_for_ocr(image_path):
    """Подготавливает изображение для OCR с улучшением качества"""
    processed_path = image_path

    if image_path.lower().endswith(".heic"):
        print("Обнаружен HEIC файл, конвертируем...")
        converted_path = convert_heic_to_jpg(image_path)
        if converted_path:
            processed_path = converted_path
        else:
            return None, "Не удалось конвертировать HEIC. Установите: pip install pillow-heif"

    print("Улучшаем качество изображения...")
    enhanced_path = enhance_image_quality(processed_path)
    if enhanced_path != processed_path:
        processed_path = enhanced_path

    processed_path = compress_image_for_api(processed_path)
    return processed_path, None