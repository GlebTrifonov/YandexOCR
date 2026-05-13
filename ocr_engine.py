import requests
import base64
import os
from config import YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_VISION_URL

def yandex_vision_ocr_advanced(image_path, api_key, folder_id):
    """Улучшенный Яндекс Cloud Vision OCR с несколькими попытками"""
    best_result = ""
    best_confidence = 0
    temp_files_to_cleanup = []

    configs = [
        {"language_codes": ["ru", "en", "be"]},
        {"language_codes": ["ru", "be"]},
        {"language_codes": ["be"]},
        {"language_codes": ["ru"]},
        {"language_codes": ["en"]},
    ]

    for config_idx, lang_config in enumerate(configs):
        processed_path = image_path
        try:
            print(f"Попытка {config_idx + 1}/{len(configs)}: {lang_config['language_codes']}")

            if config_idx == 0:
                from image_processor import prepare_image_for_ocr
                processed_path, error = prepare_image_for_ocr(image_path)
                if error:
                    return error
                if processed_path != image_path:
                    temp_files_to_cleanup.append(processed_path)

            with open(processed_path, "rb") as f:
                image_data = f.read()

            image_base64 = base64.b64encode(image_data).decode("utf-8")

            headers = {
                "Authorization": f"Api-Key {api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "folderId": folder_id,
                "analyze_specs": [
                    {
                        "content": image_base64,
                        "features": [
                            {
                                "type": "TEXT_DETECTION",
                                "text_detection_config": lang_config,
                            }
                        ],
                    }
                ],
            }

            response = requests.post(YANDEX_VISION_URL, headers=headers, json=data, timeout=30)
            result = response.json()

            if response.status_code != 200:
                continue

            current_text = ""
            current_confidence = 0

            if "results" in result and result["results"]:
                for result_item in result["results"]:
                    if "results" in result_item and result_item["results"]:
                        text_detection = result_item["results"][0].get("textDetection", {})
                        if "pages" in text_detection and text_detection["pages"]:
                            text_parts = []
                            confidence_sum = 0
                            word_count = 0

                            for page in text_detection["pages"]:
                                for block in page.get("blocks", []):
                                    for line in block.get("lines", []):
                                        for word in line.get("words", []):
                                            word_text = word.get("text", "").strip()
                                            if word_text:
                                                text_parts.append(word_text)
                                                confidence_sum += len(word_text)
                                                word_count += 1

                            if text_parts:
                                current_text = " ".join(text_parts)
                                current_confidence = confidence_sum / max(word_count, 1)

            if current_confidence > best_confidence and current_text:
                best_result = current_text
                best_confidence = current_confidence
                print(f"Улучшен результат (уверенность: {current_confidence:.1f})")

        except Exception as e:
            print(f"Ошибка в попытке {config_idx + 1}: {e}")
            continue

    for temp_file in temp_files_to_cleanup:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Удален временный файл: {temp_file}")
        except Exception as e:
            print(f"Ошибка удаления временного файла: {e}")

    return best_result if best_result else "Текст не распознан"