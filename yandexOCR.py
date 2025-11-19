import requests
import os
import pandas as pd
from time import sleep
from dotenv import load_dotenv
import re
import base64
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np

# ВАШИ ДАННЫЕ ЯНДЕКС
load_dotenv()

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')

if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
    print("❌ Не найдены ключи в .env файле")
    exit(1)


def enhance_image_quality(image_path):
    """Улучшает качество изображения для лучшего распознавания"""
    try:
        # Открываем изображение
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        # Конвертируем в серый
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Убираем шум
        gray = cv2.medianBlur(gray, 3)

        # Повышаем резкость
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        gray = cv2.filter2D(gray, -1, kernel)

        # Увеличиваем контраст
        gray = cv2.convertScaleAbs(gray, alpha=1.3, beta=0)

        # Адаптивный threshold для лучшего разделения текста и фона
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)

        # Сохраняем улучшенное изображение
        enhanced_path = image_path + '_enhanced.jpg'
        cv2.imwrite(enhanced_path, gray)

        print("   🔧 Качество изображения улучшено")
        return enhanced_path

    except Exception as e:
        print(f"   ⚠️  Ошибка улучшения качества: {e}")
        return image_path


def convert_heic_to_jpg(image_path):
    """Конвертирует HEIC в JPG используя pillow-heif"""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()

        with Image.open(image_path) as img:
            temp_path = image_path.replace('.heic', '_converted.jpg').replace('.HEIC', '_converted.jpg')
            img.convert('RGB').save(temp_path, 'JPEG', quality=85)
            print(f"   🔄 HEIC сконвертирован в JPG: {temp_path}")
            return temp_path
    except ImportError:
        return None
    except Exception as e:
        print(f"   ❌ Ошибка конвертации HEIC: {e}")
        return None


def compress_image_for_api(image_path, max_size_mb=1):
    """Сжимает изображение для API"""
    try:
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size <= max_size_mb:
            return image_path

        print(f"   📦 Сжимаем: {file_size:.1f}MB -> {max_size_mb}MB")

        with Image.open(image_path) as img:
            width, height = img.size
            if width > 2000 or height > 2000:
                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)

            temp_path = image_path + '_compressed.jpg'
            img.convert('RGB').save(temp_path, 'JPEG', quality=70, optimize=True)
            return temp_path

    except Exception as e:
        print(f"   ⚠️  Ошибка сжатия: {e}")
        return image_path


def prepare_image_for_ocr(image_path):
    """Подготавливает изображение для OCR с улучшением качества"""
    processed_path = image_path

    # Конвертируем HEIC если нужно
    if image_path.lower().endswith('.heic'):
        print("   🔄 Обнаружен HEIC файл, конвертируем...")
        converted_path = convert_heic_to_jpg(image_path)
        if converted_path:
            processed_path = converted_path
        else:
            return None, "Не удалось конвертировать HEIC. Установите: pip install pillow-heif"

    # Улучшаем качество изображения
    print("   🔧 Улучшаем качество изображения...")
    enhanced_path = enhance_image_quality(processed_path)
    if enhanced_path != processed_path:
        processed_path = enhanced_path

    # Сжимаем если нужно
    processed_path = compress_image_for_api(processed_path)

    return processed_path, None


def yandex_vision_ocr_advanced(image_path, api_key, folder_id):
    """Улучшенный Яндекс Cloud Vision OCR с несколькими попытками"""
    best_result = ""
    best_confidence = 0

    # Пробуем разные настройки
    configs = [
        {"language_codes": ["ru", "en"]},  # Русский + Английский
        {"language_codes": ["ru"]},  # Только русский
        {"language_codes": ["en"]},  # Только английский
    ]

    for config_idx, lang_config in enumerate(configs):
        try:
            print(f"   🔄 Попытка {config_idx + 1}/3: {lang_config['language_codes']}")

            # Подготавливаем изображение
            processed_path, error = prepare_image_for_ocr(image_path)
            if error:
                return error

            # Читаем и кодируем изображение в base64
            with open(processed_path, 'rb') as f:
                image_data = f.read()

            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # ЗАПРОС К YANDEX VISION API
            url = 'https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze'

            headers = {
                'Authorization': f'Api-Key {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                "folderId": folder_id,
                "analyze_specs": [{
                    "content": image_base64,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "text_detection_config": lang_config
                    }]
                }]
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)
            result = response.json()

            if response.status_code != 200:
                continue  # Пробуем следующую конфигурацию

            # Извлекаем текст и оцениваем качество
            current_text = ""
            current_confidence = 0

            if 'results' in result and result['results']:
                for result_item in result['results']:
                    if 'results' in result_item and result_item['results']:
                        text_detection = result_item['results'][0].get('textDetection', {})
                        if 'pages' in text_detection and text_detection['pages']:
                            text_parts = []
                            confidence_sum = 0
                            word_count = 0

                            for page in text_detection['pages']:
                                for block in page.get('blocks', []):
                                    for line in block.get('lines', []):
                                        for word in line.get('words', []):
                                            word_text = word.get('text', '').strip()
                                            if word_text:
                                                text_parts.append(word_text)
                                                # Оцениваем уверенность по длине слова
                                                confidence_sum += len(word_text)
                                                word_count += 1

                            if text_parts:
                                current_text = ' '.join(text_parts)
                                current_confidence = confidence_sum / max(word_count, 1)

            # Выбираем лучший результат
            if current_confidence > best_confidence and current_text:
                best_result = current_text
                best_confidence = current_confidence
                print(f"   ✅ Улучшен результат (уверенность: {current_confidence:.1f})")

            # Удаляем временные файлы
            if processed_path != image_path and os.path.exists(processed_path):
                if any(x in processed_path for x in ['_converted', '_compressed', '_enhanced']):
                    os.remove(processed_path)

        except Exception as e:
            print(f"   ⚠️  Ошибка в попытке {config_idx + 1}: {e}")
            continue

    return best_result if best_result else "Текст не распознан"


def advanced_text_correction(text):
    """Продвинутая коррекция текста"""
    if any(x in text for x in ["Ошибка", "Текст не распознан"]):
        return text

    # 1. Приводим к верхнему регистру
    text = text.upper()

    # 2. Заменяем частые OCR-ошибки
    corrections = {
        # Русские ошибки
        '0': 'О', '3': 'З', '4': 'Ч', '6': 'Б', '8': 'В',
        '1': 'I', '5': 'S', '7': 'Т', '9': 'Д',
        'СЧАСТЛИВОГО': 'СЧАСТЛИВОГО', 'ПУТИ': 'ПУТИ',
        'МИР': 'МИР', 'МЫСЛИ': 'МЫСЛИ', 'ИЗМЕНИ': 'ИЗМЕНИ',
        'ЛЮБВИ': 'ЛЮБВИ', 'СЧАСТЬЯ': 'СЧАСТЬЯ', 'ЗДОРОВЬЯ': 'ЗДОРОВЬЯ',

        # Английские ошибки
        'HELLO': 'HELLO', 'WORLD': 'WORLD', 'TEXT': 'TEXT',
        'TEST': 'TEST', 'PHOTO': 'PHOTO', 'PAPER': 'PAPER'
    }

    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)

    # 3. Убираем специальные символы (сохраняем буквы, цифры, пробелы)
    text = re.sub(r'[^А-ЯЁA-Z0-9\s]', '', text)

    # 4. Исправляем множественные пробелы
    text = re.sub(r'\s+', ' ', text).strip()

    # 5. Убираем слишком короткие "слова" (вероятно артефакты)
    words = text.split()
    filtered_words = [word for word in words if len(word) > 1 or word.isdigit()]
    text = ' '.join(filtered_words)

    return text


def analyze_text_quality(text):
    """Анализирует качество распознанного текста"""
    if not text or any(x in text for x in ["Ошибка", "Текст не распознан"]):
        return "плохое"

    # Подсчитываем статистику
    words = text.split()
    word_count = len(words)
    avg_word_length = sum(len(word) for word in words) / max(word_count, 1)

    # Процент русских букв (показатель качества для русского текста)
    russian_chars = len(re.findall(r'[А-ЯЁ]', text))
    total_chars = len(re.sub(r'\s', '', text))
    russian_ratio = russian_chars / max(total_chars, 1)

    if word_count >= 3 and avg_word_length >= 3 and russian_ratio > 0.5:
        return "отличное"
    elif word_count >= 2 and avg_word_length >= 2:
        return "хорошее"
    else:
        return "удовлетворительное"


def get_image_files(folder_path):
    """Находит все изображения в папке"""
    supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".jfif", ".webp", ".heic")
    image_files = []

    print(f"🔍 Ищем изображения в: {folder_path}")

    if not os.path.exists(folder_path):
        print(f"❌ Папка не существует: {folder_path}")
        return []

    try:
        all_files = os.listdir(folder_path)
        print(f"📁 Всего файлов в папке: {len(all_files)}")

        for file in all_files:
            file_path = os.path.join(folder_path, file)

            if os.path.isdir(file_path):
                continue

            if file.lower().endswith(supported_formats):
                image_files.append(file)
                format_type = "HEIC" if file.lower().endswith('.heic') else "изображение"
                print(f"   ✅ Найдено {format_type}: {file}")

    except Exception as e:
        print(f"❌ Ошибка чтения папки: {e}")

    return image_files


def check_heic_support():
    """Проверяет поддержку HEIC"""
    try:
        import pillow_heif
        print("✅ Поддержка HEIC: pillow-heif установлен")
        return True
    except ImportError:
        print("❌ Поддержка HEIC: не установлен pillow-heif")
        print("   Установите: pip install pillow-heif")
        return False


def check_yandex_access(api_key, folder_id):
    """Проверяет доступ к Яндекс Vision API"""
    try:
        url = 'https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze'

        headers = {
            'Authorization': f'Api-Key {api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            "folderId": folder_id,
            "analyze_specs": [{
                "content": "test",
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 401:
            return "❌ Неверный API ключ"
        elif response.status_code == 403:
            return "❌ Недостаточно прав. Добавьте роль 'ai.vision.user'"
        elif response.status_code == 404:
            return "❌ Неверный folder_id"
        elif response.status_code == 400:
            return "✅ Доступ к Яндекс Vision API разрешен"
        else:
            return f"📊 Статус: {response.status_code}"

    except Exception as e:
        return f"⚠️  Ошибка подключения: {e}"


def process_folder_enhanced_ocr(folder_path, output_file="result_enhanced.xlsx"):
    """Обработка папки с улучшенным Яндекс OCR"""
    data = []

    print(f"📁 Обрабатываем с УЛУЧШЕННЫМ Яндекс Vision: {folder_path}")
    print("=" * 60)
    print(f"🔑 API ключ: {YANDEX_API_KEY[:10]}...")
    print(f"📂 Folder ID: {YANDEX_FOLDER_ID[:10]}...")

    # Проверяем поддержку HEIC
    heic_supported = check_heic_support()

    # Проверяем доступ к Яндекс API
    print("🔐 Проверяем доступ к Яндекс Vision API...")
    access_check = check_yandex_access(YANDEX_API_KEY, YANDEX_FOLDER_ID)
    print(f"Результат проверки: {access_check}")

    if "❌" in access_check:
        print("🚫 Невозможно продолжить. Проверьте API ключ и folder_id.")
        return

    # Ищем изображения
    image_files = get_image_files(folder_path)

    print(f"🖼️ Найдено изображений: {len(image_files)}")

    if not image_files:
        print("❌ Не найдено подходящих изображений!")
        return

    print("🚀 Запускаем УЛУЧШЕННОЕ распознавание...")
    print()

    for i, filename in enumerate(image_files, 1):
        image_path = os.path.join(folder_path, filename)
        print(f"🔍 Обрабатываем [{i}/{len(image_files)}]: {filename}")

        # Используем УЛУЧШЕННЫЙ Яндекс OCR
        raw_text = yandex_vision_ocr_advanced(image_path, YANDEX_API_KEY, YANDEX_FOLDER_ID)

        # Продвинутая обработка текста
        processed_text = advanced_text_correction(raw_text)

        # Анализ качества
        quality = analyze_text_quality(processed_text)

        data.append({
            'filename': filename,
            'raw_text': raw_text,
            'processed_text': processed_text,
            'quality': quality,
            'char_count': len(processed_text)
        })

        # Показываем результат с оценкой качества
        if processed_text and "Ошибка" not in processed_text and "Текст не распознан" not in processed_text:
            print(f"   ✅ Качество: {quality.upper()}")
            print(f"   ✅ Символов: {len(processed_text)}")
            print(f"   ✨ Текст: {processed_text}")
        else:
            print(f"   ❌ {raw_text}")

        sleep(1)  # Задержка между запросами
        print("-" * 60)

    # Сохраняем результаты
    if data:
        df = pd.DataFrame(data)
        df.to_excel(output_file, index=False)

        successful = sum(1 for item in data if item['char_count'] > 0 and "Ошибка" not in item['processed_text'])
        quality_stats = df['quality'].value_counts()

        print("\n🎉 УЛУЧШЕННАЯ ОБРАБОТКА ЗАВЕРШЕНА!")
        print(f"📊 СТАТИСТИКА:")
        print(f"   • Обработано файлов: {len(data)}")
        print(f"   • Успешно распознано: {successful}")
        print(f"   • Качество распознавания:")
        for quality, count in quality_stats.items():
            print(f"     - {quality}: {count} файлов")
        print(f"   • Файл: {output_file}")


if __name__ == "__main__":
    # Установите дополнительные зависимости:
    # pip install opencv-python numpy

    folder_path = input("Введите путь к папке с изображениями: ")

    if not os.path.exists(folder_path):
        print(f"❌ Папка не существует: {folder_path}")
    else:
        process_folder_enhanced_ocr(folder_path)