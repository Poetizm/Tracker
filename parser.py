# parser.py
import re

NUM_WORDS = {
    "ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2,
    "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7,
    "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11,
    "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
    "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
    "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20,
    "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
    "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400,
    "пятьсот": 500, "шестьсот": 600, "семьсот": 700,
    "восемьсот": 800, "девятьсот": 900,
    "тысяча": 1000, "тысячи": 1000, "тысяч": 1000,
}

TYPE_KEYWORDS = {
    "PURCHASE": ["закупка", "закупки", "куплю", "купил", "приход", "закупил"],
    "SALE": ["продажа", "продажи", "продал", "продаю", "расход", "реализация"],
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _words_to_number(text: str) -> str:
    text = text.replace("полторы тысячи", "1500").replace("полтора тысячи", "1500")
    text = text.replace("полторы", "1500").replace("полтора", "1500")
    for word, num in sorted(NUM_WORDS.items(), key=lambda x: -len(x[0])):
        text = re.sub(rf"\b{word}\b", str(num), text)
    return text


def _split_digits(text: str) -> str:
    """'название1' -> 'название 1', '5шт' -> '5 шт'."""
    text = re.sub(r"([a-zA-Zа-яА-Я])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-zA-Zа-яА-Я])", r"\1 \2", text)
    return text

def _merge_numbers(text: str) -> str:
    def repl(m):
        parts = [int(p) for p in m.group(0).split()]
        # Если числа явно разного масштаба (напр. 3 и 1500) — не склеиваем
        if len(parts) >= 2 and max(parts) >= min(parts) * 10:
            return m.group(0)
        return str(sum(parts))
    return re.sub(r"\b\d+(?:\s+\d+)+\b", repl, text)


def parse_phrase(phrase: str, product_names: list, default_type: str = None):
    # 1) Нормализация
    text = _normalize(phrase)
    text = _words_to_number(text)
    text = _split_digits(text)
    text = re.sub(r"\s+", " ", text).strip()

    result = {"type": default_type, "name": None, "quantity": None, "price": None}

    # 2) Тип операции
    for op_type, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{kw}\b", text):
                result["type"] = op_type
                text = re.sub(rf"\b{kw}\b", " ", text)
                break

    # 3) Название — нормализуем так же, как фразу
    found_name = None
    for name in sorted(product_names, key=lambda n: -len(n)):
        norm_name = _normalize(name)
        norm_name = _words_to_number(norm_name)
        norm_name = _split_digits(norm_name)
        norm_name = re.sub(r"\s+", " ", norm_name).strip()
        if norm_name and re.search(rf"\b{re.escape(norm_name)}\b", text):
            found_name = name
            text = re.sub(rf"\b{re.escape(norm_name)}\b", " ", text)
            break
    result["name"] = found_name

    # 3.5) Склеиваем подряд идущие числа (семьсот двадцать -> 700 20 -> 720)
    text = _merge_numbers(text)

    # 4) Цена — "по X руб", "X рублей"
    price_match = re.search(r"(?:по\s+)?(\d+(?:[.,]\d+)?)\s*(?:руб|рублей|р\b)", text)
    if price_match:
        result["price"] = float(price_match.group(1).replace(",", "."))
        text = text[:price_match.start()] + " " + text[price_match.end():]

    # 5) Количество — "X штук", "X шт"
    qty_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:штук|штуки|шт\b)", text)
    if qty_match:
        result["quantity"] = float(qty_match.group(1).replace(",", "."))
        text = text[:qty_match.start()] + " " + text[qty_match.end():]

    # 6) Оставшиеся числа
    leftovers = re.findall(r"\b\d+(?:[.,]\d+)?\b", text)
    if result["quantity"] is not None and result["price"] is None and leftovers:
        result["price"] = float(leftovers[0].replace(",", "."))
        leftovers = leftovers[1:]
    if result["price"] is not None and result["quantity"] is None and leftovers:
        result["quantity"] = float(leftovers[0].replace(",", "."))

    # 7) Если остались ровно два числа без маркеров — первое кол-во, второе цена
    if result["quantity"] is None and result["price"] is None:
        nums = re.findall(r"\b\d+(?:[.,]\d+)?\b", text)
        if len(nums) == 2:
            result["quantity"] = float(nums[0].replace(",", "."))
            result["price"] = float(nums[1].replace(",", "."))

    return result