import re


def correct_price_ocr_errors(text):
    """Исправляет частые OCR-ошибки в ценах"""
    if not text:
        return text

    # Заменяем часто путаемые символы в ценах
    corrections = {
        'l': '1',  # маленькая L как 1
        'I': '1',  # большая i как 1
        'O': '0',  # буква O как 0
        'o': '0',  # маленькая o как 0
        'S': '5',  # S как 5
        's': '5',  # s как 5
        'Z': '2',  # Z как 2
        'z': '2',  # z как 2
        'B': '8',  # B как 8
    }

    corrected_text = text
    for wrong, correct in corrections.items():
        corrected_text = corrected_text.replace(wrong, correct)

    return corrected_text


def extract_price_from_text(text):
    """Извлекает цену из текста с исправлением OCR-ошибок"""
    if not text or any(x in text for x in ["Ошибка", "Текст не распознан"]):
        return ""

    # Сначала исправляем OCR-ошибки во всем тексте
    corrected_text = correct_price_ocr_errors(text)

    # Паттерны для поиска цен
    price_patterns = [
        # Цены с пробелом: "1 90", "2 40" (1 рубль 90 копеек)
        r'(\d+)\s+(\d{2})\b',

        # Цены с точкой/запятой
        r'(\d+[.,]\d{2})\b',

        # Цены с обозначением валюты
        r'(\d+)\s*(?:руб|р|₽|рублей|рубля)',

        # Просто числа (целые цены)
        r'(\d+)\b',

        # Любые числа от 1 до 10000
        r'\b(\d{1,4})\b'
    ]

    all_found_prices = []

    for pattern in price_patterns:
        matches = re.findall(pattern, corrected_text)
        if matches:
            for match in matches:
                if isinstance(match, tuple):  # Для паттерна с пробелом "1 90"
                    rubles, cents = match
                    price = f"{rubles}.{cents}"
                else:  # Для обычных чисел
                    price = match.replace(',', '.')

                try:
                    price_float = float(price)
                    if 0.1 <= price_float <= 10000:
                        all_found_prices.append((price_float, price))
                except ValueError:
                    continue

    # Если нашли несколько цен, берем самую вероятную (обычно саму большую)
    if all_found_prices:
        # Сортируем по величине, берем самую большую (чаще всего это правильная цена)
        all_found_prices.sort(reverse=True)
        best_price = all_found_prices[0][1]
        print(f"    Найдена цена: {best_price} (варианты: {[p[1] for p in all_found_prices]})")
        return best_price

    return ""


def extract_product_name(text, filename):
    """Извлекает название продукта из текста"""
    if not text or any(x in text for x in ["Ошибка", "Текст не распознан"]):
        return filename  # Возвращаем имя файла как запасной вариант

    # Приводим к нормальному регистру для анализа
    text = text.lower()

    # Паттерны для поиска названий культур
    patterns = [
        r'(томат|помидор|памiдор|огур[её]ц|перец|баклажан|кабач[оё]к|тыква|редис|морков[ьи]|св[её]кла)',
        r'(петрушк|укроп|базилик|шалфей|мята|розмарин|кинза|салат|щавель)',
        r'(картофел|капуст|лук|чеснок|горох|фасол|боб|кукуруз)',
        r'(клубник|малин|смородин|крыжовник|виноград|яблон|груш|слив)',
        r'(цвет[ыо]к|роза|пион|астр|хризантем|георгин|нарцисс|тюльпан)'
    ]

    # Ищем совпадения с культурой
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            culture = matches[0]

            # Ищем сорт/название после культуры
            # Пример: "томат ранняя пташка" -> "Томат Ранняя Пташка"
            culture_pos = text.find(culture)
            if culture_pos != -1:
                # Берем текст после названия культуры (2-3 слова)
                remaining_text = text[culture_pos + len(culture):].strip()
                words = re.findall(r'\b[\w-]+\b', remaining_text)[:3]  # Берем до 3 слов

                if words:
                    # Формируем название: Культура + Сорт
                    product_name = f"{culture.capitalize()} {' '.join(words).title()}"
                    return product_name

    # Если не нашли структурированное название, возвращаем первые значимые слова
    words = re.findall(r'\b[\w-]{3,}\b', text)[:2]  # Берем первые 2 слова длиной от 3 букв
    if words:
        return ' '.join(words).title()

    return filename


def advanced_text_correction(text):
    """Продвинутая коррекция текста"""
    if any(x in text for x in ["Ошибка", "Текст не распознан"]):
        return text

    # 1. Приводим к верхнему регистру
    text = text.upper()

    # 2. Заменяем частые OCR-ошибки
    corrections = {
        # Русские ошибки
        "0": "О",
        "3": "З",
        "4": "Ч",
        "6": "Б",
        "8": "В",
        "1": "I",
        "5": "S",
        "7": "Т",
        "9": "Д",
        "СЧАСТЛИВОГО": "СЧАСТЛИВОГО",
        "ПУТИ": "ПУТИ",
        "МИР": "МИР",
        "МЫСЛИ": "МЫСЛИ",
        "ИЗМЕНИ": "ИЗМЕНИ",
        "ЛЮБВИ": "ЛЮБВИ",
        "СЧАСТЬЯ": "СЧАСТЬЯ",
        "ЗДОРОВЬЯ": "ЗДОРОВЬЯ",
        # Английские ошибки
        "HELLO": "HELLO",
        "WORLD": "WORLD",
        "TEXT": "TEXT",
        "TEST": "TEST",
        "PHOTO": "PHOTO",
        "PAPER": "PAPER",
    }

    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)

    # 3. Убираем специальные символы (сохраняем буквы, цифры, пробелы)
    text = re.sub(r"[^А-ЯЁA-Z0-9\s]", "", text)

    # 4. Исправляем множественные пробелы
    text = re.sub(r"\s+", " ", text).strip()

    # 5. Убираем слишком короткие "слова" (вероятно артефакты)
    words = text.split()
    filtered_words = [word for word in words if len(word) > 1 or word.isdigit()]
    text = " ".join(filtered_words)

    return text