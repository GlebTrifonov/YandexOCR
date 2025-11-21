import os
import pandas as pd
from time import sleep
from config import YANDEX_API_KEY, YANDEX_FOLDER_ID
from file_manager import get_image_files, cleanup_processed_images
from ocr_engine import yandex_vision_ocr_advanced
from text_processor import extract_product_name, extract_price_from_text


def process_folder_enhanced_ocr(folder_path, output_file="result_enhanced.xlsx"):
    """Обработка папки с улучшенным Яндекс OCR"""
    data = []
    processed_files = []  # Список обработанных файлов для удаления

    print(f"Обрабатываем с УЛУЧШЕННЫМ Яндекс Vision: {folder_path}")
    print("=" * 60)

    image_files = get_image_files(folder_path)
    for i, filename in enumerate(image_files, 1):
        image_path = os.path.join(folder_path, filename)
        print(f" Обрабатываем [{i}/{len(image_files)}]: {filename}")

        # Получаем имя файла без расширения
        name = os.path.splitext(filename)[0]

        # Используем УЛУЧШЕННЫЙ Яндекс OCR
        raw_text = yandex_vision_ocr_advanced(image_path, YANDEX_API_KEY, YANDEX_FOLDER_ID)

        # Извлекаем название продукта
        product_name = extract_product_name(raw_text, name)

        # Извлекаем цену из текста
        extracted_price = extract_price_from_text(raw_text)

        # Добавляем данные
        data.append({
            'Наименование': product_name,  # Распознанное название продукта
            'Описание': "",  # Пустое описание
            'Цена': extracted_price,  # Извлеченная цена
        })

        # Добавляем файл в список для удаления (только временные, не исходники)
        if any(x in filename for x in ['_enhanced', '_compressed', '_converted']):
            processed_files.append(filename)

        # Показываем результат
        if raw_text and "Ошибка" not in raw_text and "Текст не распознан" not in raw_text:
            print(f"    Наименование: {product_name}")
            print(f"    Распознанный текст: {raw_text}")
            print(f"    Цена: {extracted_price if extracted_price else 'не найдена'}")
        else:
            print(f"    Ошибка: {raw_text}")

        sleep(1)
        print("-" * 60)

    # Сохраняем результаты
    if data:
        df = pd.DataFrame(data)
        df = df[['Наименование', 'Описание', 'Цена']]
        df.to_excel(output_file, index=False)

        successful = sum(1 for item in data if item['Цена'])

        print("\n ОБРАБОТКА ЗАВЕРШЕНA!")
        print(f" СТАТИСТИКА:")
        print(f"   • Обработано файлов: {len(data)}")
        print(f"   • Найдено цен: {successful}")
        print(f"   • Файл: {output_file}")

    # Удаляем временные файлы
    if processed_files:
        print(f"\n Удаляем временные файлы...")
        cleanup_processed_images(folder_path, processed_files)


if __name__ == "__main__":
    folder_path = input("Введите путь к папке с изображениями: ")
    if not os.path.exists(folder_path):
        print(f" Папка не существует: {folder_path}")
    else:
        process_folder_enhanced_ocr(folder_path)