import os
from config import SUPPORTED_IMAGE_FORMATS

def get_image_files(folder_path):
    """Находит все изображения в папке"""
    image_files = []

    print(f"Ищем изображения в: {folder_path}")

    if not os.path.exists(folder_path):
        print(f"Папка не существует: {folder_path}")
        return []

    try:
        all_files = os.listdir(folder_path)
        print(f"Всего файлов в папке: {len(all_files)}")

        for file in all_files:
            file_path = os.path.join(folder_path, file)

            if os.path.isdir(file_path):
                continue

            if file.lower().endswith(SUPPORTED_IMAGE_FORMATS):
                image_files.append(file)
                format_type = "HEIC" if file.lower().endswith(".heic") else "изображение"
                print(f"Найдено {format_type}: {file}")

    except Exception as e:
        print(f"Ошибка чтения папки: {e}")

    return image_files

def cleanup_processed_images(folder_path, processed_files):
    """Удаляет обработанные временные файлы"""
    for filename in processed_files:
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Удален временный файл: {filename}")
        except Exception as e:
            print(f"Ошибка удаления {filename}: {e}")